# encoding: utf-8
# vim: sts=4 sw=4 fdm=marker
# Author: kakkyz <kakkyz81@gmail.com>
# License: MIT
#### import
# {{{
import pdb
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib/'))
import time
from datetime import datetime, timedelta

import evernote.edam.userstore.UserStore as UserStore
import evernote.edam.userstore.constants as UserStoreConstants
import evernote.edam.notestore.NoteStore as NoteStore
import evernote.edam.type.ttypes as Types
import evernote.edam.error.ttypes as Errors
import evernote.edam.limits.constants as LimitConstants
from evernote.api.client import EvernoteClient
# }}}


class EvernoteAPI(object):
    """ interface to evernote API """
    # CLASS CONSTANT {{{
    MAXNOTES = LimitConstants.EDAM_USER_NOTES_MAX
    PAGEMAX  = 50
    NOTECONTENT_HEADER = '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd"><en-note>'
    NOTECONTENT_FOOTER = '</en-note>'
    #}}}
#### constractuor.

    def __init__(self, evernote_host, auth_token):  # {{{
        """ initialize """
	self.evernoteHost = evernote_host
	self.authToken = auth_token
        self.__setUserStore()
        self.__versioncheck()
    #}}}
#### public methods.

    def createNote(self, note):  # {{{
        authToken = self.__getAuthToken()
        return self.__getNoteStore().createNote(authToken, note)
    #}}}

    def newNote(self):  # {{{
        """ return Types.Note() """
        return Types.Note()
    #}}}

    def updateNote(self, note):  # {{{
        """ update note, return same as notesotre.updateNotenote """
        authToken = self.__getAuthToken()
        note.updated = int(time.time() * 1000)
        return self.__getNoteStore().updateNote(authToken, note)
    #}}}

    def editTag(self, note, tags):  # {{{
        """
        return note editted tag.
        tag, must canmma separated.
        """
        note.tagGuids = []
        note.tagNames = []

        localTagNames = [tag.strip() for tag in tags.split(',') if tag != '']
        taglist = self.listTags()
        # list(tag) => dict(guid,name)
        remoteTagDict = dict([(remoteTag.name, remoteTag.guid) for remoteTag in taglist])

        for localTag in localTagNames:
            if localTag in remoteTagDict:
                note.tagGuids.append(remoteTagDict[localTag])
            else:
                note.tagNames.append(localTag)

#       print ('note.tagGuids: %s') % note.tagGuids
#       print ('note.tagNames: %s') % note.tagNames
        return note
    #}}}

    def getNote(self, note):  # {{{
        """ return note include content and tagNames  """
        authToken = self.__getAuthToken()
        returnNote = self.__getNoteStore().getNote(authToken, note.guid,
                                                     True,
                                                     False,
                                                     False,
                                                     False)
        returnNote.tagNames = self.__getNoteStore().getNoteTagNames(authToken, note.guid)
        return returnNote
    #}}}

    def notesByQuery(self, query, page=0):  # {{{
        """
        return note by query.
        query format see http://www.evernote.com/about/developer/api/evernote-api.htm#_Toc290381026
        """
        noteFilter = NoteStore.NoteFilter()
        noteFilter.words = query
        noteFilter.order = Types.NoteSortOrder.UPDATED
        offset = page * EvernoteAPI.PAGEMAX

        authToken = self.__getAuthToken()
        noteList = self.__getNoteStore().findNotes(authToken, noteFilter, offset, EvernoteAPI.MAXNOTES)
        return self.__NoteList2EvernoteList(noteList)
    #}}}

    def notesByNotebook(self, notebook, page=0):  # {{{
        """ return note by notebook(notebook object). TODO:edit noteFilter more """
        noteFilter = NoteStore.NoteFilter()
        noteFilter.notebookGuid = notebook.guid
        noteFilter.order = Types.NoteSortOrder.UPDATED
        offset = page * EvernoteAPI.PAGEMAX

        authToken = self.__getAuthToken()
        noteList = self.__getNoteStore().findNotes(noteFilter, offset, EvernoteAPI.MAXNOTES)
        return self.__NoteList2EvernoteList(noteList)
    #}}}

    def notesByTag(self, tag, page=0):  # {{{
        """ return note by tag(tag object). TODO:edit noteFilter more """
        noteFilter = NoteStore.NoteFilter()
        noteFilter.tagGuids = [tag.guid]
        noteFilter.order = Types.NoteSortOrder.UPDATED
        offset = page * EvernoteAPI.PAGEMAX

        authToken = self.__getAuthToken()
        noteList = self.__getNoteStore().findNotes(authToken, noteFilter, offset, EvernoteAPI.MAXNOTES)
        return self.__NoteList2EvernoteList(noteList)
    #}}}

    def listNotebooks(self):  # {{{
        """ return listNotebooks. """
        authToken = self.__getAuthToken()

        return self.__getNoteStore().listNotebooks(authToken)
    #}}}

    def listTags(self, force=False):  # {{{
        """ return listNotebooks. TODO:cache it """

        if force or (not hasattr(self, '_EvernoteAPI__taglist')):
            self.__taglist = self.__getNoteStore().listTags(self.__getAuthToken())

        return self.__taglist

    #}}}

    def auth(self):  # {{{
        """ Authentication & set result to self.user and self.authToken """
	authToken = self.authToken
	evernote_host = self.evernoteHost
        try:
	    # client = EvernoteClient(token=authToken, sandbox=True)
	    client = EvernoteClient(service_host=evernote_host, token=authToken, sandbox=False)
        except Errors.EDAMUserException, e:
            raise StandardError("unknown errors.%s",e)
	# pdb.set_trace()
	self.userStore = client.get_user_store()
	self.noteStore = client.get_note_store()
        # set the auth result.
        # authResult.expiration && currenttime is msec
        # self.__setAuthExpiration(authResult)
    #}}}

    def refreshAuth(self):  # {{{
	self.auth()
    #}}}

#### private methods.
    # def __setAuthExpiration(self, auth):  # {{{
    #     now = datetime.now()
    #     # authResult.expiration && currenttime is msec
    #     authlimitsec = (auth.expiration  -  auth.currentTime) / 1000
    #     self.refreshAuthDataTime = now + timedelta(seconds=authlimitsec * AUTH_REFRESH_LATE)
    #     self.expirationDataTime = now + timedelta(seconds=authlimitsec)
    # #}}}

    def __setUserStore(self):  # {{{
        """ setup userStore. """
	if not hasattr( self, 'userStore' ):
	    self.auth()
    #}}}

    def __versioncheck(self):  # {{{
        """ check version. """
        versionOK = self.userStore.checkVersion("evervim",
                                           UserStoreConstants.EDAM_VERSION_MAJOR,
                                           UserStoreConstants.EDAM_VERSION_MINOR)
        if not versionOK:
            raise StandardError("evernoteAPI versionCheck NG. need update API(evervim/plugin/py/lib/*).")
    #}}}

    def __getAuthToken(self):  # {{{
        """ get authtoken.  """
        if not hasattr(self, 'authToken'):
            self.auth()

        # now = datetime.now()
        # if now > self.expirationDataTime:
        #     #  auth runout
        #     self.auth()
        # elif now > self.refreshAuthDataTime:
        #     self.refreshAuth()
        #
        return self.authToken
    #}}}

    def __getNoteStore(self):  # {{{
        """ get NoteStore.  """
        if not hasattr(self, 'noteStore'):
	    self.auth()
        return self.noteStore
    #}}}

    def __NoteList2EvernoteList(self, noteList):  # {{{
        """ get evernoteList from NoteList.  """
        returnList = EvernoteList()
        returnList.elem = noteList.notes
        returnList.maxcount = noteList.totalNotes
        # note count start by 0 because it - 1.
        returnList.maxpages = (noteList.totalNotes - 1) / EvernoteAPI.PAGEMAX
        if noteList.startIndex == 0:
            returnList.currentpage = 0
        else:
            returnList.currentpage = noteList.startIndex / EvernoteAPI.PAGEMAX

        return returnList
    #}}}

#### end class.


class EvernoteList(object):
    def __init__(self):
        self.elem = []
        self.maxcount = None
        self.maxpages = None
        self.currentpage = None

#  ---------------------------------------- eof ----------------------------------------
