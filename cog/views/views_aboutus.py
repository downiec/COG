from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required, user_passes_test, permission_required
from django.forms.models import modelformset_factory, inlineformset_factory
import string
import os
from django.conf import settings

from cog.models import *
from cog.models.constants import TABS, TAB_LABELS
from cog.forms import *
from cog.utils import *
from cog.notification import notify
from cog.services.membership import addMembership
from cog.models.utils import *
from cog.views.views_templated import templated_page_display
from cog.util.thumbnails import *

from constants import PERMISSION_DENIED_MESSAGE        

def aboutus_display(request, project_short_name, tab):
    ''' View to display an project tab page. '''
        
    template_page = 'cog/project/_project_aboutus.html'
    template_form_page = reverse('aboutus_update', args=[project_short_name, tab])
    template_title = TAB_LABELS[tab]
    return templated_page_display(request, project_short_name, tab, template_page, template_title, template_form_page)
    

@login_required
def aboutus_update(request, project_short_name, tab):
    '''View to update the project "About Us" metadata.'''

    # retrieve project from database
    project = get_object_or_404(Project, short_name__iexact=project_short_name)
    
    # check permission
    if not userHasAdminPermission(request.user, project):
        return HttpResponseForbidden(PERMISSION_DENIED_MESSAGE)
    
    # initialize formset factories for this project related objects
    OrganizationFormSet  = inlineformset_factory(Project, Organization, extra=1, can_delete=True)
    FundingSourceFormSet = inlineformset_factory(Project, FundingSource, extra=1, can_delete=True)
    
    # GET request
    if request.method=='GET':
        
        # create form object from model
        form = AboutusForm(instance=project)
        
        # create formset instances backed by current saved instances
        # assign a unix prefix to each formset to avoid colilsions
        organization_formset = OrganizationFormSet(instance=project, prefix='orgfs')
        fundingsource_formset = FundingSourceFormSet(instance=project, prefix='fundfs')
        
        # display form view
        return render_aboutus_form(request, project, tab, form, organization_formset, fundingsource_formset)

    # POST request
    else:
        # update existing database model with form data
        form = AboutusForm(request.POST, instance=project)
        organization_formset = OrganizationFormSet(request.POST, instance=project, prefix='orgfs')
        fundingsource_formset = FundingSourceFormSet(request.POST, instance=project, prefix='fundfs')
        
        if form.is_valid() and organization_formset.is_valid() and fundingsource_formset.is_valid():
            # save project data
            project = form.save()           
            oinstances = organization_formset.save()
            fsinstances = fundingsource_formset.save()
            
            # redirect to about us display (GET-POST-REDIRECT)
            return HttpResponseRedirect(reverse('aboutus_display', args=[project.short_name.lower(), tab]))
            
        else:
            # re-display form view
            if not form.is_valid():
                print 'Form is invalid  %s' % form.errors
            if not organization_formset.is_valid():
                print 'Organization formset is invalid  %s' % organization_formset.errors
            if not fundingsource_formset.is_valid():
                print 'Funding Source formset is invalid  %s' % fundingsource_formset.errors
            return render_aboutus_form(request, project, tab, form, organization_formset, fundingsource_formset)

def render_aboutus_form(request, project, tab, form, organization_formset, fundingsource_formset):
    return render_to_response('cog/project/aboutus_form.html', 
                          {'form': form, 'tab':tab,
                           'organization_formset':organization_formset, 
                           'fundingsource_formset':fundingsource_formset,
                           'title': 'Update %s %s' % (project.short_name, TAB_LABELS[tab]),
                           'project': project }, 
                          context_instance=RequestContext(request))
        
@login_required
def people_update(request, project_short_name, tab):
    
    # retrieve project from database
    project = get_object_or_404(Project, short_name__iexact=project_short_name)
    
    # check permission
    if not userHasAdminPermission(request.user, project):
        return HttpResponseForbidden(PERMISSION_DENIED_MESSAGE)
    
    # Collaborator formset
    CollaboratorFormSet  = modelformset_factory(Collaborator, 
                                                form=CollaboratorForm, # explicit reference to form to use custom text widgets
                                                extra=5, can_delete=True, exclude=('project',) )
    
    if (request.method=='GET'):
        
        # select Collaborator instances for current project
        formset = CollaboratorFormSet(queryset=Collaborator.objects.filter(project=project).order_by('last_name'))
        
        return render_people_form(request, formset, tab, project)
    
    else:
        # create formset from POST data
        formset = CollaboratorFormSet(request.POST, request.FILES,
                                      queryset=Collaborator.objects.filter(project=project).order_by('last_name'))
        
        # validate formset
        if formset.is_valid():
            
            # photo management
            for form in formset:
                
                if form.cleaned_data.get('DELETE', False):
                    try:
                        deletePhotoAndThumbnail(form.instance)
                    except Exception as error:
                        print error                    
            
            # persist formset data
            collaborators = formset.save(commit=False)
            
            # assign collaborator to project and persist
            for collaborator in collaborators:                
                collaborator.project = project
                collaborator.save()
                
                # generate photo thumbnail, 
                # after the photo has been saved to disk
                if collaborator.photo is not None:
                    try:
                        generateThumbnail(collaborator.photo.path)
                    except ValueError:
                        pass # no photo supplied
            
            # redirect to people display (GET-POST-REDIRECT)
            return HttpResponseRedirect(reverse('aboutus_display', args=[project.short_name.lower(), tab]))

            
        else:
            print 'Formset is invalid  %s' % formset.errors
            return render_people_form(request, formset, tab, project)
        

def render_people_form(request, formset, tab, project):
    
    return render_to_response("cog/project/people_form.html", 
                              { "formset": formset, "tab":tab, 
                               "title":"Update %s People" % project.short_name,
                               "project":project },
                              context_instance=RequestContext(request))
