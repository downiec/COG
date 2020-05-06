
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, HttpResponseServerError
from django.shortcuts import render
from django.template import RequestContext
import json

import datetime

import os
import re
from cog.views.utils import getQueryDict

from cog.plugins.esgf.security import esgfDatabaseManager

import traceback
import json

# Code used for react components

# Get directories for static files
package_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.dirname(package_dir)
js_dir = os.path.join(static_dir, "static/cog/cog-react/js/")
css_dir = os.path.join(static_dir, "static/cog/cog-react/css/")

# Get static list
js_files = os.listdir(js_dir)
css_files = os.listdir(css_dir)
js_files = list(map(lambda f: "cog/cog-react/js/" + f, js_files))
css_files = list(map(lambda f: "cog/cog-react/css/" + f, css_files))

# Separate source and map files
map_files = []
js_only = []
for f in js_files:
    if f.endswith(".map"):
        map_files.append(f)
    else:
        js_only.append(f)
css_only = []
for f in css_files:
    if f.endswith(".map"):
        map_files.append(f)
    else:
        css_only.append(f)

# These files are used by Django 'subscribe.html' page, to renders front-end.
react_files = {
    'css': css_only,
    'js': js_only,
    'map': map_files
}

# Example data that subscriptions front-end could receive from back-end
test_data = {
    "post_url": "/subscription/",
    "user_info": {"first": "John", "last": "Doe", "hobbies": "Programming.", "send_emails_to": "This place."},
    "activities": {"method": ["email"], "weekly": ["CMIP"], "monthly": ["CMIP6"]},
    "experiments": {"method": ["popup"], "daily": ["test", "experiment 2"], "weekly": ["test2"]},
}
# Sub_freq: [0,3], 0='Daily',1='Weekly',2='Bi-weekly', 3='Monthly'
# Sub_day: [0,6], 0='Mon',1='Tues'...6='Sun'.
# e.g: 00='Daily/Mon', 23='Biweekly/Thurs'
test_results = {
    "results": [{"subs_id": 1, "activity_id": ["CMIP", "ScenarioMIP"],  "experiment_id": ["historical", "ssp226"], "sub_freq": "01"}, 
    {"subs_id": 2, "variable_id": ["tas", "pr"],  "experiment_id": ["piControl"], "sub_freq": "12"}]
}


# To pass data to front-end, use react-props and pass it a dictionary with key-value pairs
react_props = test_data


def lookup_and_render(request):

    try:
        dbres = esgfDatabaseManager.lookupUserSubscriptions(request.user)
    except Exception as e:
        # log error
        error_cond = str(e)
        print(traceback.print_exc())
        return render(request, 'cog/subscription/subscribe_done.html', {'email': request.user.email,  'error': "An Error Has Occurred While Processing Your Request. <p> {}".format(error_cond)})

    return render(request, 'cog/subscription/subscribe_list.html', {'dbres': dbres})


def delete_subscription(request):
    res = request.POST.get('subscription_id', None)
    try:
        if res == "ALL":
            dbres = esgfDatabaseManager.deleteAllUserSubscriptions(
                request.user)
        else:
            dbres = esgfDatabaseManager.deleteUserSubscriptionById(res)
    except Exception as e:
        # log error
        error_cond = str(e)
        return render(request, 'cog/subscription/subscribe_done.html', {'error': "An Error Has Occurred While Processing Your Request. <p> {}".format(error_cond)})

    return render(request, 'cog/subscription/subs_delete_done.html')


def temp_print(request, var_name, method="POST"):
    print(request.POST)
    if request.method == "POST":
        data = json.loads(request.body)
    else:
        data = request.GET.copy()

    if(data):
        try:
            print("{} {}: {}".format(method, var_name, data[var_name]))
        except KeyError:
            print("Key error: {}".format(data))
    else:
        print("{} {}: None".format(method, var_name))


@login_required
def subscribe(request):

    # Contains the data from the front-end POST requests
    if request.method == "POST":

        # Get data from the POST request received from front-end
        data = json.loads(request.body)

        # Example obtaining data
        if data:
            for key in data.keys():
                print("{}: {}".format(key, data[key]))

        # Example response sent back to front-end
        test = {"status": "All good!", "data": data}
        return HttpResponse(json.dumps(test), content_type='application/json')

    if request.method == 'GET':
        if request.GET.get('action') == "modify":
            return lookup_and_render(request)
        else:
            return render(request, 'cog/subscription/subscribe.html', {'react_files': react_files, 'react_props': react_props})
    elif request.POST.get('action') == "delete":
        return delete_subscription(request)
    else:
        period = request.POST.get("period", -1)
        if period == -1:
            return render(request, 'cog/subscription/subscribe_done.html', {'email': request.user.email,  'error': "Invalid period"})

        subs_count = 0
        error_cond = ""
        keyarr = []
        valarr = []
        for i in range(1, 4):

            keystr = 'subscription_key{}'.format(i)
            keyres = request.POST.get(keystr, '')

            valstr = 'subscription_value{}'.format(i)
            valres = request.POST.get(valstr, '')

            if len(keyres) < 2 or len(valres) < 2:
                continue

            keyarr.append(keyres)
            valarr.append(valres)

            subs_count = subs_count + 1

        if subs_count > 0:

            try:

                esgfDatabaseManager.addUserSubscription(
                    request.user, period, keyarr, valarr)

            except Exception as e:
                # log error
                error_cond = str(e)
                return render(request, 'cog/subscription/subscribe_done.html', {'email': request.user.email,  'error': "An Error Has Occurred While Processing Your Request. <p> {}".format(error_cond), })

            return render(request, 'cog/subscription/subscribe_done.html', {'email': request.user.email, 'count': subs_count})
        else:
            return render(request, 'cog/subscription/subscribe.html', {'react_files': react_files, 'react_props': react_props})
