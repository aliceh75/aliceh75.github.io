Title: Implementing a CKAN authenticator plugin
Date: 2014-06-23
Slug: implementing-ckan-authenticator-plugin
Tags: ckan
Status: draft

Overview
--------

[CKAN](http://ckan.org) makes it possible for plugin authors to implement their own authentication mechanism - allowing users to log in to their CKAN instance using a variety of mechanism (OAuth, OpenID, etc.). Here I describe how I implemented [ckanext-ldap](http://github.com/NaturalHistoryMuseum/ckanext-ldap), a plugin that provides an LDAP authentication method for CKAN.


Repoze.who vs IAuthenticator
----------------------------

CKAN actually offers two different methods for implementing authenticators - one based on the [repoze.who WSGI authentication middleware](http://docs.repoze.org/who/2.0/), and one based on their own [`IAuthenticator`](http://docs.ckan.org/en/latest/extensions/plugin-interfaces.html#ckan.plugins.interfaces.IAuthenticator) plugin interface.

The unofficial response I got about this is that the repoze.who method is the one that comes with [Pylons](http://www.pylonsproject.org/), on top of which CKAN was build, while the other method is the one CKAN developers have implemented themselves - and is the preferred approach. So this is the approach I have taken.

Matching users
--------------






 using the `IAuthenticator` method.

Note: This was implemented for CKAN 2.2. CKAN is a rapidly evolving project, so not all of this may apply to more recent versions.

Login form
----------

For this plugin we want to allow users to use their LDAP account, but we also want to allow external users to create accounts and use those (this option can be switched off in the configuration). For ease of use we want a single form that can check both against the LDAP database and CKAN's database.

CKAN makes it easy to override the login form - indeed that is something that an authenticator plugin must do anyway as a form submitted by the standard login form does not call `IAuthenticator` methods.

To override the login template form we create our own template file (with the same subpath) at `ckanext/ldap/templates/user/login.html` and add that as a resource by implementing the `IConfigurer` interface in our plugin. The template we create is a copy of the CKAN login form - we just change the action to take us to our own controller mapped to '/ldap_loggin_handler'.

Here is the plugin.py that performs both of these:


    :::python
    import ckan.plugins as p

    class LdapPlugin(p.SingletonPlugin):
        """"LdapPlugin

        This plugin provides Ldap authentication by implementing the IAuthenticator
        interface.
        """
        p.implements(p.IConfigurer)
	p.implements(p.IRoutes, inherit=True)

        def update_config(self, config):
            """Implement IConfiguer.update_config

            Add our custom template to the list of templates so we can override the login form.
            """
            toolkit.add_template_directory(config, 'templates')

    	def before_map(self, map):
        	"""Implements Iroutes

        	Add our custom login form handler"""
        	map.connect('/ldap_loggin_handler',
                	    controller='ckanext.ldap.controllers.user:UserController',
                    	action='login_handler')
        	return map

Configuration
-------------

As a quick side note: rather than access the main configuration from our plugin, we implement `p.IConfigrable` and copy locally the configuration settings. This also allows us to check for missing settings, etc. so that the rest of the plugin can count on the settings being as expected. This is the implementation of `IConfigurable.configure` in `plugin.py`:

    :::python
    def configure(self, main_config):
        """Implementation of IConfigurable.configure"""
        # Check for required items
        for i in ['ldap.uri', 'ldap.base_dn', 'ldap.search.filter', 'ldap.username']:
            if i not in config:
                raise MissingConfigError('Configuration parameter {} is required'.format(i))
        # Copy config
        for i in ['ldap.uri', 'ldap.auth.dn', 'ldap.auth.password', 'ldap.base_dn', 'ldap.search.filter',
                  'ldap.search.alt', 'ldap.search.alt_msg', 'ldap.username', 'ldap.fullname', 'ldap.email',
                  'ldap.organization.id', 'ldap.organization.role']:
            config[i] = main_config.get(i)

Login
-----

The login process happens in our controller, `ckanext.ldap.controllers.user.UserContoller` in the `login_handler` action.





The `IAuthenticator` interface provides the following workflow:

- First, `login` is called when the `/user/login` page is accessed. This is usefull if you want to log users on a redirect, for instance when using OpenId. In our case we want users to log in via the normal login form, so we do not implement this;

- Second, `identify` is called. We will use this to look up the LDAP database, and create or assign the user if needed.

Login form
----------

The first thing to note is that when you implement an authenticator, the authentication data you get (username, keys, etc.) is expected to come from an external source. This makes it easy to implement authenticators that log you in after a redirect - for instance when using OpenId.

In our case however we want the user to enter their username and password from the CKAN interface - we will then contact the LDAP database. This means we must implement our own login form. This could be usefull anyway in the future if we wanted to handle multiple LDAP domains - though at this time the plugin does not support this.



The IAuthenticator interface
-----------------------------

I will assume you are familiar with writing CKAN extensions - if not, have a look at [the documentation on writing CKAN extensions](http://docs.ckan.org/en/ckan-2.2/extensions/index.html). The `IAuthenticator` interface provides four methods:
