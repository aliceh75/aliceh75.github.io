Title: State in back and front end web technologies
Date: 2017-03-16
Slugs: state-in-back-and-front-end-web-technologies
Tags: web, state, workflow 
Summary: Processing user requests in the backend component of websites is something that feels like a mostly solved problem. Doing the same in frontend web applications is on the other hand something that is still being improved on all the time. Here I look at how managing state differs in the two environment, and how this affects application architecture.

Processing user requests in the backend component of websites is something that feels like a mostly solved problem. Doing the same in frontend web applications is on the other hand something that is still being improved on all the time. Here I look at how managing [state](https://en.wikipedia.org/wiki/State_(computer_science)) differs in the two environment, and how this affects application architecture.

## State

HTTP requests are [stateless](https://en.wikipedia.org/wiki/Stateless_protocol), and most backend frameworks have been build to be stateless at that level. Each request comes through the backend pipeline (typically, but not always, based on a [Model View Controller](https://en.wikipedia.org/wiki/Model–view–controller) workflow) as a fresh request. Even when we use [Cookies](https://en.wikipedia.org/wiki/HTTP_cookie) we use them as another piece of stored data; our application does not keep a running state.

This gives backend applications a very clean workflow: one request comes in, it is processed in a linear fashion, and one output comes out. It doesn't matter if we get 1000 simultaneous requests, as each is processed through it's own independent pipeline. Typically additional or longer running tasks are delegated to separate workers using [message queues](https://en.wikipedia.org/wiki/Message_queue).

As a programmer (of [imperative languages](https://en.wikipedia.org/wiki/Imperative_programming)), I tend to expect state - when I set a variable to a value, I expect it to stay set. But as a programmer I also understand [scope](https://en.wikipedia.org/wiki/Scope_(computer_science)). The nature of HTTP made it that the scope of my entire backend application is a single web request. 

This was the simplest approach - it is the nature of the web that imposed this more than architectural considerations.

When it came to front end applications however, the scope of the execution was not limited - the programming model was different, because we had state. At first this felt like a release from the constraints of statelessness: we could just keep a variable to let us know where the user is at, we didn't need to work it out again and again for every interaction. If we generated a widget and put it on the page, *it just stayed there*, we didn't need to create it every time.

Great? Well, it turned out it wasn't. As front end applications became more and more advanced, this model showed it's limits: click handlers, keyboard handlers, ajax handlers all trying to modify the same state at the same time made for complicated debugging. To address this complexity, front end developers have come up with solutions such as state containers in [redux](http://redux.js.org/). Essentially this removes state manipulation away from your widgets and click handlers. Instead of manipulating the application state directly, your handlers emit actions (e.g. "the user has completed to-do with id ...") which are then caught by your state container, which then modifies the state accordingly. The state is modified in one place, and at one time.

What backend applications never had - state - is something frontend applications are still learning to tame. Having had to work this out, front end frameworks have gone one step further: with [redux](http://redux.js.org) the state is never actually modified, but rather a new state is generated from the existing state and the action. This means no code ever actually manipulates the state, and offers benefits such as easy undo and time travel debugging.

## DOM Manipulation

As backend application do not run in the browser, they have no access to the [Document Object Model (DOM)](https://en.wikipedia.org/wiki/Document_Object_Model). Backend application have no choice but to generate the HTML at every request - they cannot modify what is not there. Part of the HTML may be cached and re-used - but this is just a short cut when we know is hasn't changed: we are still generating the whole HTML (or JSON, or XML for that matter) for the request.

Javascript applications on the other hand have direct access to the DOM. As web developers our first use of Javascript was to [enhance the page](https://en.wikipedia.org/wiki/Progressive_enhancement), typically by doing in-place modifications of the DOM - if a widget got updated we could simply modify it in place, rather than re-generate the full HTML. As Javascript applications became more complex, we kept to this approach: but again this had it's difficulties. As things get complicated, it becomes harder to track what modifications have already been done to your DOM as multiple parts of your application modify the same things.

And so front end framework such as [React](https://facebook.github.io/react/) or [Angular](https://angular.io/) decided to go the other way: they never modify the DOM directly, instead whenever an input changes, the relevant HTML is re-generated. You don't need to handle the state of your widget or account for existing modifications. You just need to express how, given a set of input, the widget is rendered. In React for example your components never modify the DOM - they are rendered using [pure functions](https://en.wikipedia.org/wiki/Pure_function) which re-generate the component's HTML whenever one of it's input is modified. React and other frameworks use a [Virtual DOM](https://en.wikipedia.org/wiki/React_(JavaScript_library)#Virtual_DOM) to speed up the re-rendering of whole pages - but this is done under the hood, and users of the framework need not know of it.

## Managing state

State is, of course, what backend are often about - not the execution state as I have shown, but the state of your application. The backend deals with storing all the data, with scaling, with ensuring updates are propagated, with resolving state conflicts. And in that respect, managing state in the backend is not a solved a problem. 

Architectures will change and new ideas will come up, both on the backend and frontend. There may or may not be set architecture or programming paradigms that are better than others. What is clear is that managing state (along with processing user requests) is one of the fundamental elements that define our architecture, and that getting it right is as difficult as it is important.
