from flask import url_for, request, redirect, flash, render_template, session
from larva_library import app, db
from larva_library.models.library import WizardFormOne, WizardFormTwo, WizardFormThree
from shapely.geometry import Polygon
import datetime

@app.route('/library/wizard/page/1', methods=['GET','POST'])
def wizard_page_one():
    form = WizardFormOne(request.form)

    # temporary fix for removing current library in session, to start over
    if session.get('new_entry') is not None:
        session.pop('new_entry')
        
    if request.method == 'POST' and form.validate():
        if session.get('new_entry') is None:
            lib = dict()
            lib['Name'] = form.lib_name.data
            lib['Genus']= form.genus.data
            lib['Species'] = form.species.data
            lib['Common_Name'] = form.common_name.data
            # add to our _keywords
            _keywords = []
            _keywords.extend(lib['Name'].split(' '))
            _keywords.extend(lib['Genus'].split(' '))
            _keywords.extend(lib['Species'].split(' '))
            _keywords.extend(lib['Common_Name'].split(' '))
            lib['_keywords'] = _keywords
            session['new_entry'] = lib
            
        return redirect(url_for('wizard_page_two'))

    return render_template('wizard_page_one.html', form=form)

@app.route('/library/wizard/page/2', methods=['GET','POST'])
def wizard_page_two():
    wiz_form = WizardFormTwo(request.form)

    geo_positional_data = None

    if request.form.get('geo') is not None:
        pts = []
        geo_string = request.form.get('geo')
        point_array = geo_string.split('),(')
        for pt in point_array:
            pt = pt.split(",")
            pts.append((float(pt[1].replace(")","")),float(pt[0].replace("(",""))))
        # Create the polygon
        geo_positional_data = unicode(Polygon(pts).wkt)

    if session.get('new_entry') is None:
        # throw exception that we did not go in order
        flash('Please start the wizard from the index, page 2')
        return redirect(url_for('index'))

    elif request.method == 'POST' and wiz_form.validate():
        lib = session['new_entry']
        lib['Keywords'] = wiz_form.keywords.data
        lib['GeoKeywords'] = wiz_form.geo_keywords.data
        lib['Geometry'] = geo_positional_data
        # add the keywords to the internal keywords
        for kywrd in wiz_form.keywords.data:
            lib['_keywords'].append(kywrd)

        for kywrd in wiz_form.geo_keywords.data:
            lib['_keywords'].append(kywrd)
        
        session['new_entry'] = lib
        # copy dict into the Library structure
        return redirect(url_for('wizard_page_three'))

    return render_template('wizard_page_two.html', form=wiz_form)

@app.route('/library/wizard/page/3', methods=['GET','POST'])
def wizard_page_three():
    form = WizardFormThree(request.form)

    if session.get('new_entry') is None:
        # throw exception that we did not go in order
        flash('Please start the wizard from the index, page 3')

        if session.get('count') is not None:
            session.pop('count')

        return redirect(url_for('index'))

    elif request.args.get('add_stage') is not None:
        # increment our lifestage counter and a new entry
        count = 0
        if session.get('count') is not None:
            count = session.get('count')

        count += 1
        for i in range(0,count):
            form.lifestages.append_entry()

        session['count'] = count

    elif request.method == 'POST' and form.validate():
        lib = session['new_entry']
        lib['LifeStages'] = form.lifestages.data
        # get our datetime
        lib['Created'] = datetime.datetime.utcnow()
        # save ourself as primary user
        lib['User'] = session['user_email']
        session['new_entry'] = lib

        m_lib = db.Library()
        m_lib.copy_from_dictionary(lib)
        # ensure index our keywords
        db.libraries.ensure_index('_keywords')
        m_lib.save()

        # rebuild the index
        db.libraries.reindex()

        if session.get('count') is not None:
            session.pop('count')

        flash('Successfully added entry ' + str(m_lib._id))

        return redirect(url_for('index'))

    elif session.get('count') is not None:
        session.pop('count')

    return render_template('wizard_page_three.html', form=form)
        