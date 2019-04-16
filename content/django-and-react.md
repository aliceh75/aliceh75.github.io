Title: Setting up Django and React together
Date: 2019-02-06
Slug: django-react
Tags: python, django, react
Summary: For fullstack web developers on small projects that still want a reactive single-application interface, it can be usefull to build and serve a [React](https://reactjs.org/) application directly from [Django](https://www.djangoproject.com/). Here I show how to achieve a minimal setup with the least number of dependencies, and then build on that to include optional but common libraries.


For fullstack web developers on small projects that still want a reactive single-application interface, it can be usefull to build and serve a React application directly from Django. Here I show how to achieve a minimal setup with the least number of dependencies, and then build on that to include optional but common libraries.

This article expects you have knowledge of both Django and React, as well as basic command line skills. It is based on Django 2 and React 16. The source code from the examples in this project can be found at [https://github.com/aliceh75/django2react16]. There are 5 separate parts:

- Create a [minimal setup](#minimal-setup) that builds and serves a React application from Django;
- Add [linting and common libraries](#linting-and-common-libraries) to React;
- Use [Django authentication](#use-django-authentication) to access the React application;
- Write a [minimal API with CSRF tokens](#minimal-api-csrf);
- Add a [React testing framework](#react-testing) to test our React application.

## Approach

The approach taken is to build your React application statically, and serve it via a Django view. This approach means that you can rely on Django authentication, Django CSRF tokens, and serving related files (such as CSS) via Django. It is most suited to projects where the same developers will work both on the backend and the frontend.

The React application will be contained in a single Django application, but Javascript dependency and settings files will be stored at the top level alongside the Python ones, to make it clear this project is both Python and Javascript.

<a id='minimal-setup'></a>
## A minimal setup

### Initial structure

So the project structure will look like this:

```
django2react16/
  Pipfile             # Python dependencies
  package.json        # Javascript dependencies
  ...
  django2react16/
    frontend/
      src/            # React code
        components/   # React components
      static/
        frontend/     # Where the React application is build
      templates/
        frontend/
          index.html  # Main template for the page serving the React code
      views.py        # View to serve the React frontend
      urls.py         # Routing to the React frontend
      ...
```

### Setting up the Django project

I won't go into details about how Django is setup. If you're unsure about these steps you should check the Django documentation. On a shell terminal, and using [Pipenv](https://pipenv.readthedocs.io/en/latest/) for dependency management, the following will setup the project structure as previously described:

```shell
$ mkdir django2react16
$ cd django2react16
$ pipenv install django==2.1.7 --python=3.6
$ pipenv run django-admin startproject django2react16 .
$ mkdir django2react16/frontend
$ pipenv run ./manage.py startapp frontend django2react16/frontend
$ mkdir -p django2react16/frontend/static/frontend
$ mkdir -p django2react16/frontend/templates/frontend
$ mkdir -p django2react16/frontend/src/components
```

You may also want to apply Django's initial migrations at this point (this will use sqlite database by default):

```shell
$ pipenv run ./manage.py migrate
```

### Installing the React dependencies

We can now add the Javascript dependencies. For this you will need to have [Nodejs](https://nodejs.org/en/) and [npm](https://www.npmjs.com/) installed.

To initialse the project, run:

```shell
$ npm init
```

This command will create your initial `package.json`. The defaults are fine, feel free to customise as needed. The main thing is to leave `entry point` as `index.js`.

There exist applications such as [create-react-app](https://github.com/facebook/create-react-app) that set up an initial project for you. They tend to add a lot of dependencies that are not strictly required, so I prefer to install things manually. A basic React setup is actually much simpler than a lot of these ready-made applications, templates and tutorials would have you believe. These are the Javascript dependencies we will need:

- For React, we need the main React library [react](https://www.npmjs.com/package/react) and the React library that is specific to web environements (as opposed to React native), [react-dom](https://www.npmjs.com/package/react-dom) ;
- To translate modern Javascript ([ES6 and beyond](https://en.wikipedia.org/wiki/ES6#6th_Edition_-_ECMAScript_2015)) and [React JSX](https://reactjs.org/docs/introducing-jsx.html) into Javascript that is supported by browsers, we will need the [Babel compiler](https://babeljs.io/). The dependencies we need are [@babel/core](https://www.npmjs.com/package/@babel/core) for the main library, [@babel/preset-env](https://www.npmjs.com/package/@babel/preset-env) and [@babel/preset-react](https://www.npmjs.com/package/@babel/preset-react) for preset babel configurations that work with React (writting such configurations by hand would be quite a task);
- To package the React application into a file we can serve via the web, we will need [Webpack](https://webpack.js.org/). The dependencies are [webpack](https://www.npmjs.com/package/webpack), [webpack-cli](https://www.npmjs.com/package/webpack-cli) and to integrate babel with webpack we need [babel-loader](https://www.npmjs.com/package/babel-loader).

So, from our project root, we can install those by doing:

```shell
$ npm install react react-dom --save
$ npm install @babel/core @babel/preset-env @babel/preset-react webpack webpack-cli babel-loader --save-dev
```

Note that we use `--save` for runtime libraries, and `--save-dev` for build time dependencies. In practice it would work either way. If you run into version issues you may want to check the exact versions of these packages in the Git repository for this article.

### Configuring the Javascript build system

We need a little bit of configuraton. First, we need to tell Babel what presets to use. To do this create a file `.babelrc` in your project root with the following:

```json
{
    "presets": [
        "@babel/preset-env", "@babel/preset-react"
    ]
}
```

And we need to tell Webpack to use babel. To do this create a file `webpack.config.js` in your project root with the following:

```js
module.exports = {
  module: {
    rules: [
      {
        test: /\.js$/,
        exclude: /node_modules/,
        use: {
          loader: "babel-loader"
        }
      }
    ]
  }
};
```

Finally we're going to tell npm how to build the application. Open your `package.json` and edit the `script` section to add the following commands:

```js
  ...
    "scripts": {
      "build-dev": "webpack --mode development --devtool source-map ./django2react16/frontend/src/index.js --output ./django2react16/frontend/static/frontend/main.js",
      "build": "webpack --mode production ./django2react16/frontend/src/index.js --output ./django2react16/frontend/static/frontend/main.js"
  },
  ...
```

The `build` command is used for production, while the `build-dev` command is used for development. Both commands save the resulting javascript in `django2react16/frontend/static/frontend/main.js` (and the dev command will add a source map file along side it).

Note we're not ready to run that build command yet - we need to put the files in place first.


### Bootstraping Django side

We have a few things to put in place to serve the application.

#### The main index.html template file

This file is in `dango2react16/frontend/templates/frontend/index.html` and contains the following:

```html
{% load static %}
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Django2React16</title>
</head>
<body>
  <div id="app"></div>
  <script src="{% static 'frontend/main.js' %}"></script>
</body>
</html>
```

All it does is create the `#app` element React is going to bind to, and include our Javascript.

#### The views and urls

Next we need to create the view that will serve the file. Create `django2react16/frontend/views.py` with the following:

```python
from django.shortcuts import render


def index(request):
    return render(request, 'frontend/index.html')
```

Create `dango2react16/frontend/urls.py` with the following:

```python
from django.urls import path

from django2react16.frontend import views

urlpatterns = [
    path('', views.index),
]
```

And in the main `urls.py` at `django2react16/urls.py` add the path to the frontend view - your `urls.py` would look something like:

```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('', include('django2react16.frontend.urls')),
    path('admin/', admin.site.urls),
]
```

Finally add the `frontend` app to your `INSTALLED_APPS` in settings.py:

```python
...
INSTALLED_APPS = [
    ...
    'django2react16.frontend'
]
```

### Initial React application

Now we're ready to add a basic React application. First we need to create our entry point - `index.js` which will create the `App` component and attach it to the `#app` HTML element we added in our template. So `django2react16/frontend/src/index.js` would look like this:

```javascript
import React from "react";
import ReactDOM from "react-dom";
import App from "./components/App";

const wrapper = document.getElementById("app");
wrapper ? ReactDOM.render(<App />, wrapper) : null;
```

Our main `App` component in `django2react16/frontend/src/components/App.js` will be like this:

```javascript
import React from "react";
import AppContent from "./AppContent";

class App extends React.Component {
  render() {
    return <div>
      <h1>Django2React16!</h1>
      <AppContent />
    </div>;
  }
}

export default App;
```

Note that for the sake of demonstrating importing and using React components I've created a second component, `AppContent`, used in the main `App` component. The `AppContent` component is in `dango2react16/frontend/src/components/AppContent.js` and looks like this:

```javascript
import React from "react";

class AppContent extends React.Component {
  render() {
    return <div>Hello World</div>;
  }
}

export default AppContent;
```

### Let's run it!

We're done! You should first build the React application by running:

```shell
$ npm run build-dev
```

And you can then start the Django server:

```shell
$ pipenv run ./manage.py runserver
```

You can now navigate to `http://localhost:8000` and see your brand new React application!


### Final notes

If you're going to commit this to version control, you'll want to ignore the following files:

- `node_modules`, the folder when Javascript dependencies are downloaded;
- `django2react16/frontend/static/frontend/main.js` the generate Javascript application;
- `django2react16/frontend/static/frontend/main.js.map` the source map for the Javascript application.

As well as usual Django files.

So your `.gitignore` would look like:

```
db.sqlite3
node_modules
django2react16/frontend/static/frontend/main.js
django2react16/frontend/static/frontend/main.js.map
```

<a id="linting-and-common-libraries"></a>
## Adding linting and some common libraries to React

Linting is useful on many levels - it finds bugs, avoids wasting time on style issues, etc. There are default linting styles for React and I will use those. One of the things the default React linting settings expect are [PropTypes](https://reactjs.org/docs/typechecking-with-proptypes.html) - these allow for type checking of component properties, and are a useful debuging tool.

The default ES6 way to add PropTypes is by adding to your class' prototypes. We can use [class properties](https://github.com/tc39/proposal-class-fields) instead. Class properties is (at the time of writing) a new javascript feature still under proposal - however there is a babel plugin to support it, and it's widely used in the React world.

So let's start by adding out new dependencies:
```shell
$ npm install @babel/plugin-proposal-class-properties eslint eslint-plugin-react babel-eslint --save-dev
```

We need to configure eslint to tell it what style we want. Here I use 2 space indentation, semi-colons at end of instructions, and the default React settings. Create the file `.eslintrc.json`in your project root with the following:

```json
{
    "env": {
        "browser": true,
        "es6": true
    },
    "extends": ["eslint:recommended", "plugin:react/recommended"],
    "parser": "babel-eslint",
    "parserOptions": {
        "ecmaFeatures": {
            "jsx": true
        },
        "ecmaVersion": 2018,
        "sourceType": "module"
    },
    "plugins": [
        "react"
    ],
    "rules": {
        "indent": ["error", 2],
        "linebreak-style": ["error", "unix"],
        "semi": ["error", "always"]
    },
    "settings": {
        "react": {
            "createClass": "createReactClass",
            "pragma": "React",
            "version": "detect",
            "flowVersion": "0.53"
        },
        "propWrapperFunctions": [
            "forbidExtraProps",
            {"property": "freeze", "object": "Object"},
            {"property": "myFavoriteWrapper"}
        ]
    }
}
```

Finally we need to tell `npm` how to run the linting. To do this, add a `lint` entry in the `scripts` section of the file `package.json`:
```
  ...
  "scripts": {
    ...
    "lint": "eslint ./django2react16/frontend/src",
    ...
  }
  ...
```

This will lint the javascript files in `django2react16/frontend/src`. You can test it now by running:


```shell
$ npm run lint
```

If you test this on the `minimal-setup` branch of the associated Git repository, you will see that it reports linting errors (fixed on the `linting-and-common-libraries` branch).

To use the PropTypes, we need to tell Babel to compile this new feature. To do this, edit `.babelrc` and add "@babel/plugin-proposal-class-properties" as a plugin, like this:

```
{
    "presets": [
        "@babel/preset-env", "@babel/preset-react"
    ],
    "plugins": [
        "@babel/plugin-proposal-class-properties"
    ]
}
```

To demonstrate PropTypes, we're going to add a single property, `counter`, to our `AppContent` component. The property should be a number and is required. `AppContent.js` now looks like this:


```js
 import React from "react";
 import PropTypes from "prop-types";
 
 class AppContent extends React.Component {
   static propTypes = {
     counter: PropTypes.number.isRequired
   };
 
   render() {
     return <div>Hello World: {this.props.counter}</div>;
   }
 }
```

And we need to add the property from our `App.js`, which now looks like this:

```js
 class App extends React.Component {
   render() {
     return <div>
       <h1>Django2React16!</h1>
       <AppContent counter={1} />
     </div>;
   }
 }
```

We can now rebuild with `npm run buil-dev` and see the new code in action. Proptype validation happens at runtime, and in development mode only. If you were to ommit the `counter` property for `AppContent` you see a runtime error in the browser console.


<a id="use-django-authentication"></a>
## Use Django Authentication

<a id="minimal-api-csrf"></a>
## Implement a minimal API with CSRF validation

<a id="react-testing"></a>
## Add a React testing framework
