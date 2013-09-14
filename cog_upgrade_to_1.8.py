# Python script to upgrade the content of an existing COG installation
import sys, os, ConfigParser

sys.path.append( os.path.abspath(os.path.dirname('.')) )
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from cog.models import *
from cog.models.logged_event import log_instance_event
from django.db.models.signals import post_save
from cog.models import SearchFacet, SearchProfile, SearchGroup, Folder
from cog.config.search import config_project_search
from django.conf import settings
from cog.models.utils import create_project_search_profile, get_or_create_default_search_group
from django.core.exceptions import ObjectDoesNotExist

print 'Upgrading COG to version 1.7'

def renameFolder(folder, newName):
    print "Renaming folder: %s to: %s" % (folder.name, newName)
    folder.parent = None
    folder.name = newName
    folder.save()
    

# loop over projects, folders
'''
for project in Project.objects.all():
    
    folders = Folder.objects.filter(project=project)
    
    for folder in folders:
        # old top-level folder
        if folder.name.endswith("Bookmarks"):
            newName = "Bookmark Folder"
            print 'Renaming folder: %s to: %s' % (folder.name, newName)
            folder.name = newName
            folder.save()
        else:
            pass
            #if project.short_name=='CoG' and folder.name=='Presentations':
            #    renameFolder(folder, 'Presentations')
'''

# rename tabs
for project in Project.objects.all():
    for tab in ProjectTab.objects.filter(project=project):
        if tab.label == 'Communication':
            print 'Renamed tab %s to: Communications' % tab
            tab.label = 'Communications'
            tab.save()
                
# remove obsolete pages
oldpages = ['getinvolved','code','support']
for project in Project.objects.all():
    posts = Post.objects.filter(project=project)
    for post in posts:
        for oldpage in oldpages:
            url = "/projects/%s/%s/" % (project.short_name.lower(), oldpage)
            if post.url==url or post.url == url[0:-1]:
                print 'Deleting page: %s' % post.url
                post.delete()