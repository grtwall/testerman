# -*- coding: utf-8 -*-
##
# This file is part of Testerman, a test automation system.
# Copyright (c) 2008-2009 Sebastien Lefevre and other contributors
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
##

##
# LDAP client probe, based on python-ldap, the Python wrapper over
# OpenLDAP libraries.
#
##

import ProbeImplementationManager

import ldap
import ldap.modlist
import threading

class LdapClientProbe(ProbeImplementationManager.ProbeImplementation):
	"""
	= Identification and Properties =

	Probe Type ID: `ldap.client`

	Properties:
	|| '''Name''' || '''Type''' || '''Default value''' || '''Description''' ||
	|| `server_url` || string || `'ldap://127.0.0.1:389'` || LDAP server url, including protocol to use (ldap or ldaps) ||
	|| `ldap_version` || integer || 2 || LDAP server version
	|| `username` || string || None (undefined) || The DN entry to bind, if not provided through a request ||
	|| `password` || string || empty || The password to use by default for binding ||
	|| `timeout` || float || 60.0 || The maximum amount of time allowed to perform a search/write/delete operation before raising an error response ||
	
	(no properties)

	= Overview =

	This probe simulates a LDAP client that can connect to a LDAP server
	to perform the following LDAP operations:
	 * bind
	 * unbind
	 * search
	 * add and update
	 * delete
	
	It can connect to LDAP v2 and v3 servers, using a standard or a secure (ldaps, SSL/TLS)
	connection.
	
	SASL connections are currently not interfaced.

	By default, the probe automatically binds using the `default_username` and `default_password` prior
	to execute a search/write/delete command, unless an explicit bind command was performed by the user before.

	The probe automatically unbinds on unmap.[[BR]]
	
	To add or update an entry, use a `WriteCommand` message. The probe
	automatically detects if it should be a new entry (don't forget mandatory
	attributes according to the entry's schema) or an update. In case of an update:
	 * only provided attributes are modified. The other ones are left unchanged
	 * all values of the existing attributes are replaced with the new ones (no values merge)
	 * you can delete an attribute by specifying an empty value list for it
	
	Notes:
	 * Bind, write and unbind operations are synchronous, i.e. 
	it's not use arming a timer to cancel them from the userland: they
	are not cancellable, and only return when they are complete. However,
	you still must wait for a `BindResult` or `WriteResult`
	before assuming the operation is complete.
	 * The synchronous bind and write implementations may be replaced with asynchronous
	equivalent ones day. This 	won't have any impact on your testcases
	if you wait for the `BindResult` and `WriteResult` as explained above.

	== Availability ==

	All platforms.

	== Dependencies ==

	This probe depends on the openldap library and its associated Python wrapper.
	
	On Debian-based system, this is `python-ldap` and its dependencies.

	== See Also ==
	
	
	= TTCN-3 Types Equivalence =

	The test system interface port bound to such a probe complies with the `LdapPortType` port type as specified below:
	{{{
	type union LdapCommand
	{
		BindCommand   bind,     // binds to the server set in properties, with the defaut or given credentials
		UnbindCommand unbind,   // unbinds from the server
		SearchCommand search,   // searches entries according to a ldap search filter
		WriteCommand  write,    // updates or adds a new entry or attribute
		DeleteCommand delete,   // deletes an entry
		AbandonCommand abandon, // abandon the current command, if any
		CancelCommand abandon,  // cancel the current command, if any (only supported on RFC3909 compliant server)
	}

	type record BindCommand {
		charstring username optional, // the distinguished name of the entry to bind
		charstring password optional,
	}

	type any UnbindCommand;

	type record SearchCommand {
		charstring baseDn,
		charstring filter, // should we use a default filter (objectClass=*) ?
		charstring scope optional, // enum in 'base', 'subtree', 'onelevel', defaulted to 'base'
		record of charstring attributes optional, // defaulted to an empty list, i.e. all attributes are returned
	}

	type record WriteCommand {
		charstring dn,
		record of Attribute attributes optional, // defaulted to an empty list
	}

	type record Attribute {
		record of <natural type> <name> // dynamic names, natural types (charstring/universal charstring, int, double, octetstring, ...)
	}

	type record DeleteCommand {
		charstring dn,
	}

	type any AbandonCommand;

	type any CancelCommand;
	
	type boolean DeleteResult;
	
	type boolean BindResult;

	type boolean UnbindResult;
	
	type record of SearchEntry SearchResult;
	
	type record SearchEntry {
		charstring dn,
		record of Attribute attributes,
	}
	
	type boolean WriteResult;

	type charstring ErrorResponse;

	type union LdapResponse
	{
		BindResult bindResult,
		UnbindResult unbindResult,
		DeleteResulet deleteResult,
		SearchResult searchResult,
		WriteResult writeResult,
		ErrorResponse error,
	}

	type port LdapPortType message
	{
		in  LdapCommand;
		out LdapResponse;
	}
	}}}
	"""
	def __init__(self):
		ProbeImplementationManager.ProbeImplementation.__init__(self)
		self._mutex = threading.RLock()
		self._server = None
		self._pendingRequest = None
		self.setDefaultProperty('server_url', 'ldap://127.0.0.1:389')
		self.setDefaultProperty('ldap_version', 2)
		self.setDefaultProperty('username', None)
		self.setDefaultProperty('password', '')
		self.setDefaultProperty('timeout', 60.0)

	# ProbeImplementation reimplementation

	def onTriUnmap(self):
		self.getLogger().debug("onTriUnmap()")
		self.abandon()
		self._unbind()

	def onTriMap(self):
		self.getLogger().debug("onTriMap()")
		self.abandon()
		self._unbind()
	
	def onTriSAReset(self):
		self.getLogger().debug("onTriSAReset()")
		self.abandon()
		self._unbind()
	
	def onTriExecuteTestCase(self):
		self.getLogger().debug("onTriExecuteTestCase()")
		self.abandon()
		self._unbind()

	def onTriSend(self, message, sutAddress):
		# Exceptions are turned into Error messages sent back to userand, according of the current
		# attempted operation.
		if not isinstance(message, (list, tuple)) and not len(message) == 2:
			raise Exception("Invalid message format - please read the ldap probe documentation")
		command, args = message
		
		if command == 'bind':
			self._checkArgs(args, [ ('username', self['username']), ('password', self['password']) ])
			self.bind(args['username'], args['password'])
		
		elif command == 'unbind':
			self.unbind()
		
		elif command == 'search':
			self._checkArgs(args, [ ('scope', 'subtree'), ('baseDn', ''), ('attributes', []), ('filter', None) ])
			if self._getPendingRequest():
				# Exception or error response ? -> Exception. This is not a "protocol" related error, but a local usage error.
				raise Exception('Another request is pending. Please abandon or cancel it first.')
			self.search(args['baseDn'], args['filter'], args['scope'], args['attributes'])
		
		elif command == 'write':
			self._checkArgs(args, [ ('dn', None), ('attributes', []) ])
			if self._getPendingRequest():
				# Exception or error response ? -> Exception. This is not a "protocol" related error, but a local usage error.
				raise Exception('Another request is pending. Please abandon or cancel it first.')
			self.write(args['dn'], args['attributes'])
		
		elif command == 'delete':
			self._checkArgs(args, [ ('dn', None) ])
			if self._getPendingRequest():
				# Exception or error response ? -> Exception. This is not a "protocol" related error, but a local usage error.
				raise Exception('Another request is pending. Please abandon or cancel it first.')
			self.delete(args['dn'])

		elif command == 'abandon':
			self.abandon()

		elif command == 'cancel':
			self.cancel()
		
		else:
			raise Exception("Invalid command (%s)" % command)
	
	def _getPendingRequest(self):
		self._lock()
		ret = self._pendingRequest
		self._unlock()
		return ret
	
	def _setPendingRequest(self, request):
		self._lock()
		self._pendingRequest = request
		self._unlock()
	
	def _lock(self):
		self._mutex.acquire()
	
	def _unlock(self):
		self._mutex.release()
	
	def _unbind(self):
		if self._server:
			self._server.unbind()
			self._bound = False
			self._server = None

	def unbind(self):
		try:
			self._unbind()
			self.triEnqueueMsg(('unbindResult', True))
		except Exception, e:
			self.triEnqueueMsg(('error', 'Error while binding: %s' % str(e)), self['server_url'])
	
	def abandon(self):
		self._lock()
		if self._pendingRequest and self._server:
			pendingRequest = self._pendingRequest
			self._pendingRequest = None
			self._unlock()
			self._server.abandon(pendingRequest)
		else:
			self._unlock()

	def cancel(self):
		self._lock()
		if self._pendingRequest and self._server:
			pendingRequest = self._pendingRequest
			self._pendingRequest = None
			self._unlock()
			self._server.cancel(pendingRequest)
		else:
			self._unlock()
	
	def _bind(self, username, password):
		self.getLogger().debug('Binding to %s as %s/%s...' % (self['server_url'], username, password))
		self._server = ldap.initialize(self['server_url'])
		# Generates an exception in case of a binding (or connection) error.
		self._server.bind_s(username, password)
	
	def _onResult(self, request, result, operationName):
		"""
		Called by the waiting thread when receiving a result.
		@type  request: the request ID as returned by the associated operation trigger
		@param request: the request ID as returned by the associated operation trigger
		@type  result: userland message
		@param result: the result to the operation, already formatted as a userland message
		@type  operationName: string
		@param operationName: the operation type/name the result is for ('search', 'write', ...)
		"""
		self._lock()
		if self._pendingRequest == request:
			self._pendingRequest = None
			self._unlock()
			# Not cancelled. Raises the response.
			self.getLogger().debug("Received %s response to pending request %s: %s" % (operationName, request, result))
		else:
			self._unlock()
			self.getLogger().warning("Late %s response received for request %s: discarded" % (operationName, request))
		
		self.triEnqueueMsg(('%sResult' % operationName, result), self['server_url'])
	
	def _onError(self, request, errorString):
		"""
		Called by any waiting response threads in case of an error when waiting
		for request's response.
		
		Raises a userland event if the request was still pending.
		
		@type  request: the request ID as returned by the associated operation trigger
		@param request: the request ID as returned by the associated operation trigger
		@type  errorString: unicode
		@param errorString: the error string
		
		"""
		if self._pendingRequest == request:
			self.getLogger().warning("Error response for pending request %s: %s" % (request, errorString))
			self.triEnqueueMsg(('errorResponse', errorString), self['server_url'])
		else:
			self.getLogger().warning("Late (and discarded) error response received for request %s: %s" % (request, errorString))
		self._pendingRequest = None
	
	def bind(self, username, password):
		try:
			self._bind(username, password)
			self.triEnqueueMsg(('bindResult', True))
		except Exception, e:
			self.triEnqueueMsg(('error', 'Error while binding: %s' % str(e)), self['server_url'])
	
	def search(self, basedn, filter_, scope, attributes):
		self.getLogger().debug('Searching %s from %s (scope %s, attributes: %s)' % (filter_, basedn, scope, attributes))
		if scope == 'subtree':
			s = ldap.SCOPE_SUBTREE
		elif scope == 'onelevel':
			s = ldap.SCOPE_ONELEVEL
		elif scope == 'base':
			s = ldap.SCOPE_BASE
		else:
			raise Exception('Invalid scope (%s): only the following are supported: subtree, oneleve, base' % scope)
		if not self._ensureBind():
			return
		self._pendingRequest = self._server.search(basedn, s, filter_, attributes)
		# Now starts a thread to wait for our results.
		th = threading.Thread(target = self._waitForSearchResult, kwargs = dict(request = self._pendingRequest, timeout = self['timeout']))
		th.start()
	
	def _waitForSearchResult(self, request, timeout):
		"""
		Executed in a dedicated thread.
		"""
		res = False
		resultSet = []
		try:
			# Let's pool the result regularly, while we have a pending request.
			resultType, resultData = self._server.result(request, timeout = timeout)
			self.getLogger().debug('Search result: %s' % resultData)
			for (dn, attributes) in resultData:
				resultSet.append({'dn': dn, 'attributes': attributes}) 
			res = True
		except ldap.USER_CANCELLED:
			pass
		except ldap.NO_SUCH_OBJECT:
			res = True
			resultSet = []
		except Exception, e:
			self._onError(request, ProbeImplementationManager.getBacktrace())
	
		if res:
			self._onResult(request, resultSet, 'search')

	def delete(self, dn):
		if not self._ensureBind():
			return
		self._pendingRequest = self._server.delete(dn)
		# Now starts a thread to wait for our results.
		th = threading.Thread(target = self._waitForDeleteResult, kwargs = dict(request = self._pendingRequest, timeout = self['timeout']))
		th.start()

	def _waitForDeleteResult(self, request, timeout):
		"""
		Executed in a dedicated thread.
		"""
		res = False
		deleteResult = False
		try:
			# Let's pool the result regularly, while we have a pending request.
			resultType, resultData = self._server.result(request, timeout = timeout)
			self.getLogger().debug('Delete result: %s' % resultData)
			res = True
			# resultData is an empty list if OK
			# deleteResult = resultData 
			deleteResult = True
		except ldap.USER_CANCELLED:
			pass
		except ldap.NO_SUCH_OBJECT:
			res = True
			deleteResult = False
		except Exception, e:
			self._onError(request, ProbeImplementationManager.getBacktrace())
	
		if res:
			self._onResult(request, deleteResult, 'delete')
	
	def write(self, dn, attributes):
		"""
		Synchronous implementation for now...
		"""
		if not self._ensureBind():
			return

		completed = False
		try:
			try:
				# a list of tuples (dn, attribute dict)
				searchResult = self._server.search_s(dn, ldap.SCOPE_BASE)
				if not searchResult:
					# Let's add it
					self._server.add_s(dn, ldap.modlist.addModlist(attributes))
					completed = True
				elif len(searchResult) == 1:
					# Let's modify the entry
					# modifyMolist(previous values, new values)
					self._server.modify_s(dn, ldap.modlist.modifyModlist(searchResult[0][1], attributes, ignore_oldexistent = 1))
					completed = True
				else:
					# Cannot write multiple DNs.
					self.triEnqueueMsg(('error', 'Multiple entries correspond to this dn, cannot update'), self['server_url'])
			except ldap.NO_SUCH_OBJECT:
				# Let's add it
				self._server.add_s(dn, ldap.modlist.addModlist(attributes))
				completed = True
		except Exception, e:
			self.triEnqueueMsg(('error', 'Error while updating/adding some data:\n%s' % ProbeImplementationManager.getBacktrace()), self['server_url'])

		if completed:
			self.triEnqueueMsg(('writeResult', True))
		
	
	def _ensureBind(self):
		"""
		Makes sure we are bound to a server.
		If not, bind it.
		"""
		ret = False
		if not self._server:
			try:
				self._bind(self['username'], self['password'])
				ret = True
			except Exception, e:
				self.triEnqueueMsg(('error', 'Error while binding: %s' % str(e)), self['server_url'])
		else:
			ret = True
		return ret
		
				
	
ProbeImplementationManager.registerProbeImplementationClass('ldap.client', LdapClientProbe)

