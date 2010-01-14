#!/usr/bin/env python
# -*- coding: utf-8 -*-
##
# This file is part of Testerman, a test automation system.
# Copyright (c) 2009 Sebastien Lefevre and other contributors
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
# Testerman server-side administration console.
# 
# Experimental.
#
##


import readline
import cmd
import sys



##
# A cisco-like command-line shell, using
# "inline" value tree representations,
# based on a syntax that can be described with ASN.1 primitives
# (sequence, choice, integer, string)
#
#
# Support for autocompletion.
# Not based on Python standard's cmd module due to a
# different way to autocomplete tokens and propose next ones.
#
# Low-level input handling, however, is based on readline.
#
#
# Usage:
# - create a CommandContext and register one or multiple commands
# in it. These commands have a syntax tree based on a SequenceNode.
# - ... ?
# 
#
##


from CiscoCommandShell import *





##
# Some almost unit tests to test the parsing and completion capabilities
##

def parseTest():
	"""
	Some unit tests
	"""
	def deploy(component, archive, version = None, branch = ("testing", None)):
		print "Deploying package %s as component %s, version %s, branch %s..." % (archive, component, version, branch[0])
	
	
	cm = ContextManager()
	
	deployment = cm.createRootContext("deployment", "component deployment context")
	
	deployNode = SequenceNode("deploy a new component on server")
	deployNode.addField("branch", ChoiceNode("deployment branch").addChoice("stable", NullNode("stable component")).addChoice("testing", NullNode("testing component")), True)
	deployNode.addField("component", StringNode("component name"))
	deployNode.addField("archive", StringNode("path to archive"))
	deployNode.addField("version", StringNode("version to announce"), True)
	deployment.registerCommand("deploy", deployNode, deploy)


	cmd = "deploy component test branch testing archive /tmp/ version 1.0.0"
	print cmd
	print cm.getFormattedSuggestions(cmd.split(' '))

	cmd = "deploy component test branch stable archive /tmp/"
	print cmd
	print cm.getFormattedSuggestions(cmd.split(' '))

	cmd = "deploy component test archive"
	print cmd
	print cm.getFormattedSuggestions(cmd.split(' '))

	cmd = "d"
	print cmd
	print cm.getFormattedSuggestions(cmd.split(' '))

	cmd = "deploy"
	print cmd
	print cm.getFormattedSuggestions(cmd.split(' '))

	cmd = "deploy "
	print cmd
	print cm.getFormattedSuggestions(cmd.split(' '))

	cmd = "deploy comp"
	print cmd
	print cm.getFormattedSuggestions(cmd.split(' '))

	cmd = "deploy component "
	print cmd
	print cm.getFormattedSuggestions(cmd.split(' '))

	cmd = "deploy component t"
	print cmd
	print cm.getFormattedSuggestions(cmd.split(' '))

	cmd = "deploy component t "
	print cmd
	print cm.getFormattedSuggestions(cmd.split(' '))


##
# Administration functions
##

import ComponentContext

def main():

	adminShell = CmdContextManagerAdapter("Welcome to Testerman Administration Console")

	# Root context
	rootContext = adminShell.createRootContext("testerman", "testerman administration")
	
	adminShell.registerContext("component", ComponentContext.Context(), rootContext)

	try:
		adminShell.run()
	except ShellExit:
		print
		sys.exit(0)
	except KeyboardInterrupt:
		print
		sys.exit(0)
	

if __name__ == "__main__":
	main()
	#parseTest()
	
