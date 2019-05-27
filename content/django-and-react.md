Title: Walkthrough: setting up Django and React project
Date: 2019-02-06
Slug: django-react
Tags: python, django, react
Summary: For fullstack web developers on small projects that still want a reactive single-application interface, it can be usefull to build and serve a [React](https://reactjs.org/) application directly from [Django](https://www.djangoproject.com/). Here I show how to achieve a minimal setup with the least number of dependencies, and then build on that to include optional but common libraries.


For fullstack web developers on small projects that still want a reactive single-application interface, it can be usefull to build and serve a React application directly from Django. Here I show how to achieve a minimal setup with the least number of dependencies, and then build on that to include optional but common libraries.

This article is build as a walkthrough. You may want to follow the steps here exactly, just skip around looking at ideas for solving particular problems, and/or look at the source code at [https://github.com/aliceh75/django2react16](https://github.com/aliceh75/django2react16). The article is aimed at Django developers who want to integrate React - as such while all Django steps are included, they may not be explained in detail. The article expects some understanding of the fundamental concepts behind both Django and React, and experience with the command line. The walkthrough uses Django 2 and React 16, and the examples here were run on an Ubuntu 18.04 LTS machine.

There are 5 separate parts:

- Create a [minimal setup](#minimal-setup) that builds and serves a React application from Django;
- Add [linting and common libraries](#linting-and-common-libraries) to React;
- Use [Django authentication](#use-django-authentication) to access the React application;
- Write a [minimal API with CSRF tokens](#minimal-api-csrf);
- Add a [React testing framework](#react-testing) to test our React application.

## Approach

The approach taken is to build your React application statically, and serve it via a Django view. This approach means that you can rely on Django authentication, Django CSRF tokens, and serving related files (such as CSS) via Django. It is most suited to projects where the same developers will work both on the backend and the frontend.

<a id='minimal-setup'></a>
## A minimal setup

### Initial structure

The project structure will look like this:

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
### Pre-requisites

To follow the steps exactly you should have Python 3.6, [Pipenv](https://pipenv.readthedocs.io/en/latest/), [Nodejs](https://nodejs.org/en/) and [npm](https://www.npmjs.com/) installed.

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

We can now add the Javascript dependencies. To initialise the project, run:

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

The `build` command is used for production, while the `build-dev` command is used for development. Both commands save the build javascript application in `django2react16/frontend/static/frontend/main.js` (and the dev command will add a source map file along side it).

Note we're not ready to run that build command yet - we need to put the files in place first.


### Bootstraping Django side

We have a few things to put in place to serve the application. The first thing is the main `index.html` template file.

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

```jsx
import React from "react";
import ReactDOM from "react-dom";
import App from "./components/App";

const wrapper = document.getElementById("app");
wrapper ? ReactDOM.render(<App />, wrapper) : null;
```

Our main `App` component in `django2react16/frontend/src/components/App.js` will be like this:

```jsx
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

```jsx
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

We can now rebuild with `npm run buil-dev` and see the new code in action. Proptype validation happens at runtime, and in development mode only. If you were to ommit the `counter` property for `AppContent` you would see a runtime error in the browser console.


<a id="use-django-authentication"></a>
## Use Django Authentication

One of the advantages of combining Django and React as described in this article is that we can use Django to authenticate users, rather than having to implement this React side.

Fist we need to add the default Django authentication URLs in `django2react16/urls.py` by adding this line to the `urlpatterns`:

```python
    path('accounts/', include('django.contrib.auth.urls')),
```

We also need to create a template for the login form. First create the registration template folder:

```shell
$ mkdir -p django2react16/frontend/templates/registration
```

And then add the file `django2react16/frontend/templates/registration/login.html`:

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Django2React16</title>
</head>
<body>
  <h2>Login</h2>
  <form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Login</button>
  </form>
</body>
</html>
```

Finally we just need to mark the view that serves the React application as requiring login. To do this we're going to add the `@login_required` decorator to the view `index` in `django2react16/frontend/views.py`. The file now looks like:

```python
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def index(request):
    return render(request, 'frontend/index.html')
```

And that's it - only logged in users can now access our React App. Django provides mechanisms for logging in, resetting passwords, managing users, etc. To test it, you can add a new super user by doing:

```shell
$ pipenv run ./manage.py createsuper
```

And then navigating to `localhost:8000` and logging in as that user.

<a id="minimal-api-csrf"></a>
## Implement a minimal API with CSRF validation

### CSRF

We're now going to add an API with CSRF validation, again relying on Django to provide the CSRF mechanisms.

When using backend-generated forms, it is normal practice for the bakcend to include the CSRF token as a hidden field in the form. In this case any form would be generated on the frontend, so we need to comunicate the CSRF token differently. We do this by passing it as a cookie. To make sure this happens, you need to add a decorator to the view serving the React app.

So in `django2react16/frontend/views.py`, import the following decorator:

```python
from django.views.decorators.csrf import ensure_csrf_cookie
```

And then decorate the view:

```python
@login_required
@ensure_csrf_cookie
def index(request):
    return render(request, 'frontend/index.html')
```

### The API

Now to write an API, we'll want to have some data to share. We're going to store, and increase, the counter we created in a previous section. So we're going to create a simple model in `django2react16/frontend/models.py`:

```python
from django.db import models


class Counter(models.Model):
    value = models.IntegerField()
```

To create and apply the migrations for the model run:

```
$ pipenv run ./manage.py makemigrations frontend
$ pipenv run ./manage.py migrate
```

And we're going to create a very basic API. When invoked it will simply increase the value of the given counter by 1, and return the new value. We'll add the API alongside the existing view in `django2react16/frontent/views.py`:

```python
@require_http_methods(["POST"])
@login_required
def increase_counter(request, counter_pk):
    counter = Counter.objects.get(pk=counter_pk)
    counter.value = counter.value + 1
    counter.save()

    return JsonResponse({'value': counter.value})
```

The API code should be self-explanatory: only accept logged-in users, only accept POST methods, increase the value of the given counter, and return a JSON object with the new value. Note that Django will automatically force CSRF validation on POST methods, so that is already covered. For the above code to work, you need these new imports in `views.py`:

```python
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django2react16.frontend.models import Counter
```

And to ensure our API request are routed, add the following to `urlpatterns` in `django2react16/frontend/urls.py`:

```python
path('api/<int:counter_pk>', views.increase_counter)
```

### Providing initial data to the React app

Each instance of the React app will have it's own counter - we'll create it when the page is loaded, and provide it's primary key to the react app. Let's rewrite the `index` view in `django2react16/frontend/views.py`:

```python
@login_required
@ensure_csrf_cookie
def index(request):
    counter = Counter(value=1)
	counter.save()
    return render(request, 'frontend/index.html' {
		'counter_pk': counter.pk,
        'counter_value': counter.value
    })
```

In the `render` call we're passing the primary key and counter value as context - now in the view's template we'll simply store these values as a javascript variables, which will get read when executed in the browser. In `django2react16/frontend/templates/frontend/index.html` we'll add, before the existing `script` tag:

```html
<script>
  var counter_pk={{counter_pk}};
  var counter_value={{counter_value}};
</script>
```

At this stage you can now reload the application in the browser, and inspect the value of `counter_pk` in the javascript console. It should increase with every page reload.

### Using the API from React

We're now done with the Python side of things. Let's get to the React side of things. We're going to use the `App` component's local state to store the counter value (we won't be using any additional third party state management library).

The state will be initialised during the component's `componentDidMount` call, and the counter value from the state will be passed down to the `AppContent` component. We'll also now write a handler on the `App` component to increase the counter value - making the API call and setting the new counter value when that completes. This handler will also be passed to the `AppContent` component.

Remember we need to read the CSRF token, which is stored as a cookie. For that we'll add another dependency, [js-cookie](https://www.npmjs.com/package/js-cookie):

```shell
$ npm install js-cookie --save
```

The API call will be made with the native [fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API), and we will use [Promises](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise) to handle asynchronous resolution. While both `fetch` and `Promise` are native on recent browsers, they may still be missing on older browsers. So we're going to use [Polyfills](https://en.wikipedia.org/wiki/Polyfill_(programming)) to ensure that functionality is always available. We'll use [whatwg-fetch](https://www.npmjs.com/package/whatwg-fetch) and [promise-polyfill](https://www.npmjs.com/package/promise-polyfill). These need to be installed:

```shell
$ npm install promise-polyfill whatwg-fetch --save
```

And they also need to be loaded when the application starts. We do this in `django2react16/frontend/src/index.js` simply by importing the libraries before starting React:

```jsx
// Promise polyfill for older browsers
import 'promise-polyfill/src/polyfill';

// Fetch polyfill for older browsers
import 'whatwg-fetch';
```

We're now ready to implement our changes to `django2react16/frontend/src/components/App.js`, which now looks like this:

```jsx
import Cookies from "js-cookie";
import React from "react";

import AppContent from "./AppContent";

class App extends React.Component {
  state = {
    counter_value: 0
  }

  render() {
    return <div>
      <h1>Django2React16!</h1>
      <AppContent
        counter={this.state.counter_value}
        onIncCounter={() => this.handleIncCounter()}
      />
    </div>;
  }

  componentDidMount() {
    this.setState({counter_value: window.counter_value});
  }

  handleIncCounter() {
    fetch(`/api/${window.counter_pk}`, {
      method: 'POST',
      credentials: 'include',
      mode: 'same-origin',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-CSRFToken': Cookies.get('csrftoken')
      }
    }).then((response) => {
      if (response.status >= 200 && response.status < 300) {
        return response;
      } else {
        var error = new Error(response.statusText);
        error.response = response;
        throw error;
      }
    }).then((response) => {
      return response.json();
    }).then((data) => {
      this.setState({counter_value: data.value});
    }).catch((error) => {
      alert(error);
    });
  }
}

export default App;
```

We now need to add a button in `AppContent` to increase the counter. When clicked, the button will invoke `handleIncCount` on the App component, which is passed down as the `onIncCounter` property. So the `AppContent` component in `django2react16/frontend/src/components/AppContent.js` now looks like this:

```jsx
class AppContent extends React.Component {
  static propTypes = {
    counter: PropTypes.number.isRequired,
    onIncCounter: PropTypes.func.isRequired
  };

  render() {
    return <div>
      <p>Hello World: {this.props.counter}</p>
      <button onClick={this.props.onIncCounter}>Increment</button>
    </div>;
  }
}
```

That's it. You can now rebuild your React code with:

```shell
$ npm run build-dev
```

And reload the page, and try the new functionality.

### Sending data to the API

In this simple example we didn't send any data to the API - all we needed was the counter pk which was provided in the URL. In a more complex scenario where you want to send data to the API, one way of doing this is using JSON. You can add a `body` field to the `fetch` call, and store JSON in it, eg:

```jsx
fetch(url, {
    method: 'POST',
    credentials: 'include',
    mode: 'same-origin',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'X-CSRFToken': Cookies.get('csrftoken')
    },
    body: JSON.stringify(data)
  });
```
In your Django view you would then load the data this way:

```python
    data = json.loads(request.body)
```

<a id="react-testing"></a>

## Add a React testing framework
