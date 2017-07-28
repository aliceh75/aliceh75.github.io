Title: Re-implementing the CKAN API for performance
Date: 2015-04-28
Slug: reimplementing-ckan-api-for-performance
Tags: ckan, python
Summary: [CKAN](http://ckan.org), an open source data portal platform, provides an API for fetching everything from datasets to individual records. Here we look at how CKAN's architecture allows developers to transparently re-implement the datastore API, and how this was used to improve performance by switching all searches to using a [Solr](https://lucene.apache.org/solr/) backend.

[CKAN](http://ckan.org), an open source data portal platform, provides an API for fetching everything from datasets to individual records (using the [Datastore extension](http://docs.ckan.org/en/latest/maintaining/datastore.html)). Here we look at how CKAN's architecture allows developers to transparently re-implement the datastore API, and how this was used to improve performance by switching all searches to using a [Solr](https://lucene.apache.org/solr/) backend.

The issue arose while working on the [Natural History Museum's Data Portal](http://data.nhm.ac.uk): with 2.8M rows, which over 70 fields each, and a user interface that allows users to search on any combination of fields we felt that PostgreSQL was providing poor performance. At this scale using more hardware was an option, but we felt this was not the right solution when Solr could run the same searches 20 times faster.

CKAN's architecture
-------------------

CKAN implements an [RPC style API](http://docs.ckan.org/en/latest/api/index.html) which exposes all of CKAN's core features. What is particularly useful is that internal calls are also routed via the same API: CKAN's [`get_action`](http://docs.ckan.org/en/latest/extensions/plugins-toolkit.html#ckan.plugins.toolkit.get_action) is used to return the functions that can be used to perform various actions, such as creating a dataset or performing a datastore query.

This approach has numerous advantages:

- Decouples interface and implementation;
- Enables plugins to override actions;
- Provides a consistent interface, whether developing an extension or a client;
- Server side extensions can use the same API without going through de/serialization process.

Of course there are some disadvantages - one of them is the absence of an ORM style interface: all data is provided simply as a dictionary, and is manipulated by invoking functions.

Re-implementing the datastore API
---------------------------------

Thanks to CKAN's architecture, we were able to re-implement the API completely and provide a compatible API that uses Solr, rather then PostgreSQL, for datastore searches: [ckanext-datasolr](https://github.com/NaturalHistoryMuseum/ckanext-datasolr).

To override calls to the [datastore_search](http://docs.ckan.org/en/latest/maintaining/datastore.html#ckanext.datastore.logic.action.datastore_search) API endpoint, we created a plugin that implements the [IRoutes interface](http://docs.ckan.org/en/latest/extensions/plugin-interfaces.html#ckan.plugins.interfaces.IRoutes) so we could change where calls to `datastore_search` would be routed. This is done simply as:

    :::python
    import ckan.plugins as p 

    class DataSolrPlugin(p.SingletonPlugin):
        p.implements(p.IRoutes, inherit=True)

        def before_map(self, map): 
            map.connect(
                'datasolr',
                '/api/3/action/datastore_search',
                controller='api',
                action='action',
                logic_function='datastore_solr_search',
                ver=u'/3'
            )

We need to declare our logic function `datastore_solr_search` by implementing the [IActions](http://docs.ckan.org/en/latest/extensions/plugin-interfaces.html#ckan.plugins.interfaces.IActions) interface in our plugin:

    :::python
    # ...
    from ckanext.datasolr.logic.action import datastore_solr_search

    class DataSolrPlugin(p.SingletonPlugin):
        # ...
        p.implements(p.interfaces.IActions)

        # ...
        def get_actions(self):
            return {
                'datastore_solr_search': datastore_solr_search
            }

And this is it - all calls, internal or external, to `datastore_search` will be routed to `ckanext.datasolr.logic.action.datastore_solr_search` - we are now free to re-implement the API as we wish (do check the [implementation](http://github.com/NaturalHistoryMuseum/ckanext-datasolr) for details).

Making the new plugin extensible
--------------------------------

CKAN's [interface architecture](http://docs.ckan.org/en/latest/extensions/plugin-interfaces.html) which allows plugins to easily add functionality to other parts of the system is another element that allowed us to implement this plugin. As such, and given that the [datastore extension has it's own interface](https://github.com/ckan/ckan/blob/master/ckanext/datastore/interfaces.py), it seemed like a good idea to implement one for our plugin.

This is done simply by creating a class that inherits from [ckan.plugins.interfaces.Interface](https://github.com/ckan/ckan/blob/master/ckan/plugins/interfaces.py):

    :::python
    from ckan.plugins import interfaces

    class IDataSolr(interfaces.Interface):
        def datasolr_validate(self, context, data_dict, field_types):
            return data_dict
        
        def datasolr_search(self, context, data_dict, field_types, query_dict):
            return query_dict

Plugins that want to add their own validation and/or to modify the search expression just need to implement this interface. They need to declare this by including `ckan.plugins.implements(IDataSolr)`.

The `ckanext_datasolr` code can now invokes all plugins that extend it by doing, for example:

    :::python
    from ckan.plugins import PluginImplementations

    for plugin in PluginImplementations(IDataSolr):
        data_dict = plugin.datasolr_validate(
            self.context, data_dict, self.fields
        )

Extensibility is important for any sort of framework - and finding the right balance between that and architectural complexity is often tricky. CKAN's approach is in some aspects rigid, but the fact we were able to re-implement this API is testament to it's effectiveness.
