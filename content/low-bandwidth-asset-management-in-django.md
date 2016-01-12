Title: Low bandwidth asset management in Djando
Date: 2015-10-01
Slug: low-bandwidth-asset-management-in-django
Tags: django, python
Summary: Low bandwidth implies high latency - when implementing a site for low bandwidth conditions we must pay attention to the packaging and number of assets we include on each page. Here we look at an approach for combining assets in Django while preserving the relationship between each asset and the code that required it.

<div class="note">This post was originally writen for, and published on, <a href="http://aptivate.org/en/blog/2015/10/01/low-bandwidth-asset-management-in-django/">Aptivate's site</a></div>

Low bandwidth implies high latency - in other words, when implementing a site for low bandwidth conditions we must pay attention to the size of our assets, but also to the packaging and number of assets we include on each page.

When it comes to Django, the de-facto solution for managing assets is [django-assets](https://django-assets.readthedocs.org/): it will minify and compress our assets and, crucially, allow us to merge all assets of a type into a single file.

For websites that are mostly server side, and unless our assets change on a very regular basis, this is generally what we want. Not all the CSS or Javascript may be used on all the pages, but the cost of downloading an extra file under high latency condition is often higher than the cost of adding a bit of extra CSS in a file that is, anyway, cached by the browser and only loaded once.

To be able to build a single file that contains all our CSS (and a single file that contains all our Javascript) `django-assets` must know about the assets ahead of time - they must be defined statically in one place. This can be in Python code:

    :::python
    from  django_assets  import  Bundle,  register
    js  =  Bundle('common/jquery.js',  'site/base.js',  'site/widgets.js',
                  filters='jsmin',  output='gen/packed.js')
    register('js_all',  js)

Or in a template:

    :::html
    {%  load  assets  %}
    {%  assets  "js_all"  %}
          <script type="text/javascript" src="{{  ASSET_URL  }}"></script>
    {%  endassets  %} 

But in both cases the list of resources that is to be included in the same file must be declared in the same place. There is no way for two unrelated pieces of code to declare which assets they want, and have those included in a single asset file. This is a problem, because we lose a lot of information and structure - there is a link between the Python code that generates a page, the CSS that styles it and the Javascript that manipulates it. By moving all our assets in a single place, we lose that link.

Here is a simple approach to address this problem and re-introduce the structure that we would otherwise lose:

* Include all resources statically in one (python) file, `assets.py`;
* In the same file create a function named `require_assets`. All this function does is raise an exception if the required asset is not part of the list that gets build statically;
* Code that expects or needs a particular asset, say `my_asset.css`, can than invoke `require_asset('my_asset.css')`. If this is missing, an exception will be raised.

This way we re-introduce the link that we have lost when we moved our list of assets to `asset.py`: If I read the python code that generates a page, and I see a call to `require_asset` I know which assets are expected for that page. Conversely, if I wonder why a certain asset is included, I can search the code for calls to `require_asset` that include that asset. Raising an exception in `require_asset` also ensures we do not forget to add our assets in `assets.py`.

Here is an example implementation of `assets.py`:

    :::python
    from django_assets import Bundle, register

    _assets = [
        'fonts/font-awesome-4.3.0/css/font-awesome.css',
        'less/bootstrap.less',
        'mysite/mysite.css',
        'js/jquery.min.js',
        'bootstrap/js/bootstrap.min.js',
    ]


    class AssetMissing(Exception):
        """ Exception raised when an asset is missing """
        pass


    def require_assets(*assets):
        """ Ensure the given assets are included in the page's assets
        Args:
            assets: List of assets
        Raises:
            AssetMissing: If any of the asset is missing
        """
        global _assets
        for asset in assets:
            if asset not in _assets:
                raise AssetMissing("Missing asset: {}".format(asset))


    register('javascript_assets', Bundle(
        *[a for a in _assets if a.endswith('.js')],
        filters='jsmin', output='js/javascript_assets.js'
    ))
    register('css_assets', Bundle(
        *[a for a in _assets if a.endswith('.css') or a.endswith('.less')],
        filters='less, cssmin', output='css/css_assets.css',
        depends=['less/*.less']
    ))

This is a very lightweight implementation, and there are a number of obvious improvements that could be done:

* Dependency management;
* Versioning;
* A template tag to call require_asset from templates.

But already this simple and lightweight implementation re-introduces the semantics and structure that we had lost when moving all our asset declaration in a single place.
