Title: Implementing a CKAN permission plugin
Date: 2014-06-23
Slug: implementing-ckan-permission-plugin
Tags: ckan
Summary: [CKAN](http://ckan.org) implements a permission system based on roles, permissions and authorization functions which can be overridden by plugins. I used to this to implement the [ckanext-userdatasets](https://GitHub.com/NaturalHistoryMuseum/ckanext-userdatasets) plugin. The aim of this plugin is to allow certain types of users to create datasets in an organization without having the permission to edit or delete other users' datasets. Here I describe how I went about implementing this plugin.


Overview
--------

[CKAN](http://ckan.org) implements a permission system based on roles, permissions and authorization functions which can be overridden by plugins. I used to this to implement the [ckanext-userdatasets](https://GitHub.com/NaturalHistoryMuseum/ckanext-userdatasets) plugin. 

CKAN users within an organization can have one of three roles:

- _admins_ who have all permissions on the organization and it's datasets;
- _editors_ who can create, edit and delete any dataset in the organization;
- _members_ who can view private datasets.

The aim of this plugin is to allow users with the _member_ role to create datasets in an organization without having the permission to edit or delete other users' datasets. CKAN does not currently allow us to create new roles - so what the plugin does is _add_ permissions to the member role. We do this rather than _remove_ permissions from the editor role because we want to keep the editor role separate from the admin role; but also because _adding_ permissions means that, should the plugin fail, you'd end up with some users having less permissions, rather than some users having more permissions.

Note: This was implemented for CKAN 2.2. 

Overriding auth functions
-------------------------

I will assume you are familiar with writing CKAN extensions - if not, have a look at [the documentation on writing CKAN extensions](http://docs.ckan.org/en/ckan-2.2/extensions/index.html), and in particular the page on [implementing the IAuthFunctions plugin interlace](http://docs.ckan.org/en/ckan-2.2/extensions/tutorial.html#implementing-the-iauthfunctions-plugin-interface)

So the first thing to do is to identify which authentication functions to override. In this case, we want to override anything that has to do with creating or editing packages and related objects. A look at `ckan.logic.auth` will tell what us what authorization functions exist. From there we can see that we want to override:

- `package_create`
- `package_delete`
- `package_update`
- `resource_create`
- `resource_delete`
- `resource_update`

We do not want to fully override the functionality of those functions; we only want to treat a special case: allow a user who has the `member` role in an organization to create a dataset, and edit/delete datasets they have created. For all other cases we want to fallback on CKAN's default implementation. CKAN does not provide a mechanism for falling back to the default function (though [there is an implementation in the works](https://github.com/ckan/ckan/issues/1784)), but it is easy enough to implement - I've created my own `get_default_auth` and `get_default_action` which I can easily replace when CKAN supports this.

To make it easy to map various auth functions to each other I have used the same structure used by CKAN itself, so my functions reside in `ckanext.userdatasets.logic.auth.create.package_create`, `ckanext.userdatasets.logic.auth.delete.package_delete`, etc. and we can map them using a simple loop. Note that the plugin also provides support for [CKAN's 1251 branch](https://github.com/ckan/ckan/tree/1251-resource-view), so it also checks for `resource_view_*` functions and override them if they exist.

Here is the code for plugin.py at that stage of the implementation:

    :::python
    import importlib
    import ckan.plugins as p

    config = {}


    class UserDatasetsPlugin(p.SingletonPlugin):
        """"UserDatasetsPlugin

        This plugin replaces dataset and resource authentication calls to allow
        users with the 'Member' role to create datasets, and edit/delete their
        own datasets (but not others).
        """

        p.implements(p.IAuthFunctions)
        p.implements(p.IConfigurable)

        def configure(self, main_config):
            """Implementation of IConfigurable.configure"""
            config['default_auth_module'] = config.get('userdatasets.default_auth_module', 'ckan.logic.auth')

        def get_auth_functions(self):
            """Implementation of IAuthFunctions.get_auth_functions"""
            # We override all of create/update/delete for packages, resources and resource views.
            auth_functions = {}
            for action in ['create', 'update', 'delete']:
                default_module = importlib.import_module(config['default_auth_module'] + '.' + action)
                uds_module = importlib.import_module('ckanext.userdatasets.logic.auth.' + action)
                for atype in ['package', 'resource', 'resource_view']:
                    fn_name = atype + '_' + action
                    if hasattr(default_module, fn_name) and hasattr(uds_module, fn_name):
                        auth_functions[fn_name] = getattr(uds_module, fn_name)

            return auth_functions


    def get_default_auth(ftype, function_name):
        """Return the default auth function

        @param type: The type of auth function (create/update/delete)
        @param function: Name of function. It must exists.
        @return: The auth function
        """
        default_module = importlib.import_module(config['default_auth_module'] + '.' + ftype)
        return getattr(default_module, function_name)

CKAN provides a number of usefull functions to test permissions (though in practice CKAN plugins should not import CKAN functions directly, we would otherwise have to re-implement those functions exactly as they are). In addition to those, we add two of our own to help our auth functions:

- `user_is_member_of_package_org` which allows us to check if a given user has the member role on the given package's organization; and
- `user_owns_package_as_member` which allows us to check if the given user created the given package and has the member role in the package's organization.

The implementation is as follows:

    :::python
    from ckan import logic
    from ckan.new_authz import users_role_for_group_or_org

    def user_is_member_of_package_org(user, package):
        """Return True if the package is in an organization and the user has the member role in that organization

        @param user: A user object
        @param package: A package object
        @return: True if the user has the 'member' role in the organization that owns the package, False otherwise
        """
        if package.owner_org:
            role_in_org = users_role_for_group_or_org(package.owner_org, user.name)
            if role_in_org == 'member':
                return True
       return False

    def user_owns_package_as_member(user, package):
        """Checks that the given user created the package, and has the 'member' role in the organization that owns the package.
        
        @param user: A user object
        @param package: A package object
        @return: True if the user created the package and has the 'member' role in the organization to which package belongs.
                 False otherwise.
        """
        if user_is_member_of_package_org(user, package):
            return package.creator_user_id and user.id == package.creator_user_id

        return False

From there the implementation of the auth functions is straight forward. As an example here is `resource_create`:

    :::python
    from ckan.logic.auth import get_package_object, get_resource_object
    from ckan.new_authz import users_role_for_group_or_org, has_user_permission_for_some_org
    from ckanext.userdatasets.plugin import get_default_auth


    def resource_create(context, data_dict):
        user = context['auth_user_obj']
        package = get_package_object(context, data_dict)
        if user_owns_package_as_member(user, package):
            return {'success': True}
        elif user_is_member_of_package_org(user, package):
            return {'success': False}

        fallback = get_default_auth('create', 'resource_create')
        return fallback(context, data_dict)

One major **gotcha** is that `package_create` may be called without a defined organization. If that is the case, the function should return success if the given user can create packages on any organization. This is not documented but obvious from CKAN's implementation.


Override validators
--------------------

Unfortunately overriding auth functions is not enough. Some of CKAN's validators also perform auth tests - an issue [that should be resolved soon](https://github.com/ckan/ckan/issues/1775). Until the issue is resolved, we must override those validators to allow packages to be created.

The validators that need to be overridden have to be identified by trial and error. `package_create` (itself an action) calls `ckan.lib.plugins.plugin_validate` on the form data, which uses the validator `ckan.logic.validators.owner_org_validator` and which in turns calls `ckan.new_authz.has_user_permission_for_group_or_org`. The latter fails us. Unfortunately, nothing in the call stack below `package_create` can be overridden using CKAN's API, so the only option is to override that one.

What I have done is re-implement (ahem, copy) the functionality, but changed the list of validators used to validate the input - replacing, in that particular context, `ckan.logic.validators.owner_org_validator` with our own copy. The change is minor:

    :::python
    from ckan.logic.validators import owner_org_validator as default_oov
    from ckanext.userdatasets.logic.validators import owner_org_validator as uds_oov
    [.....]
    def package_create(context, data_dict):
        [....]
        package_type = data_dict.get('type')
        package_plugin = lib_plugins.lookup_package_plugin(package_type)
        if 'schema' in context:
            schema = context['schema']
        else:
            schema = package_plugin.create_package_schema()
        # We modify the schema here to replace owner_org_validator by our own
        if 'owner_org' in schema:
            schema['owner_org'] = [uds_oov if f is default_oov else f for f in schema['owner_org']]

        [.....]

The implementation of `ckanext.userdatasets.logic.validators.owner_org_validator` itself is straightforward:

    :::python
    import ckan.lib.navl.dictization_functions as df
    from ckan.new_authz import users_role_for_group_or_org
    from ckan.logic.validators import owner_org_validator as default_oov

    missing = df.missing

    def owner_org_validator(key, data, errors, context):
        owner_org = data.get(key)
        user = context['auth_user_obj']
        if owner_org is not missing and owner_org is not None and owner_org != '':
            role = users_role_for_group_or_org(owner_org, user.name)
            if role == 'member':
                return

        default_oov(key, data, errors, context)

`ckan.logic.action.update.package_update` had to be overridden in the same way as `package_create` was.

Other Overrides
---------------

A final action that we had to override is one that lists the organizations in which a given role can create a dataset - `organization_list_for_user`. As per the auth functions, we can override the action by implementing `IActions` and our implementation can treat our special case and fallback to the default implementation otherwise.


Conclusion
-----------

CKAN's plugin model has allowed us to plug into it's authorization system and add permissions at a level (the dataset) that was not initial supported. CKAN allowed us to do this without resorting to hacks (even though it required a lot of code digging!). Doing so however has forced us to reproduce the entirety of the `package_create` and `package_update` actions, which ties the plugin very closely to CKAN's implementation and thus to the version of CKAN the plugin runs on. Hopefully this is issue will be solved in the near future - allowing the plugin to function by only overriding auth functions, not actions.


