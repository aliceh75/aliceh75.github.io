Title: Measuring delay when using webview with Go
Date: 2018-12-11
Slug: measuring-delay-when-using-webview-with-go
Tags: go, webview
Summary: Serge Zaitsev's [webview](https://github.com/zserge/webview) library allows us to use a native browser webview in applications written in [the Go programming language](https://golang.org/). Amongst other things it allows us to invoke Go methods from the webview's Javascript code, and I wanted to measure how much delay that would introduce.

## Introduction

Serge Zaitsev's [webview](https://github.com/zserge/webview) library allows us to use a native browser webview in applications written in [the Go programming language](https://golang.org/). Amongst other things it allows us to invoke Go methods from the webview's Javascript code, and I wanted to measure how much delay that would introduce.

These tests were done using Go 1.11.2 and webview v0.0.0-20181018084947-f390a2df9ec5, running on a amd64 Linux system, and webview used Webkit 605.1.15. These tests are not meant to be comparative, or about absolute performance. Rather I wanted an idea of the order of magnitude of the delays introduced, to inform architectural decisions on building a Go application with webview.

The impatient may jump to the [conclusion](#conclusion).

## The basic test

I created a simple page with two buttons: one called "Go" which would invoke a Go method to change the value of a variable, and one called "Js" which would change the value of the variable directly.

I then used a [Proxy](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Proxy) object to watch the variable, and measure the time between the button click and the time the variable was changed. The fact I used a Proxy object meant I could not use webview's [Bind](https://github.com/zserge/webview#how-to-communicate-between-native-go-and-web-ui) method to share data between Go and the webview. When you do this webview rewrites the object browser side on change, deleting the Proxy object. So Instead I used Go to run a line of Javascript to change the variable's value.

Here is the Go code. Two things to note:

- The `Eval` method runs in the browser the string it was given. This is enough functionality to have a back-and-forth between the browser and Go and measure the time it takes;
- I've used  [go-bindata](https://github.com/go-bindata/go-bindata) to package the Js in the Go binary

<br/>
```go
package main

import (
	"github.com/zserge/webview"
)

var view webview.WebView
type RPC struct {
    Version string
}

func (rpc *RPC) Eval(js string) {
    view.Eval(js)
}

func main() {
	view = webview.New(webview.Settings{
		Title: "GoWebViewPerf",
        Debug: true,
	})
	defer view.Exit()

    rpc := RPC{"0.0.1"}

    view.Dispatch(func() {
        view.Bind("Remote", &rpc)
		view.Eval(string(MustAsset("gowebviewperf.js")))
	})
	view.Run()
}
```

And here is the Javascript code. It creates two buttons which change the value of an object's property (to a random string), and uses Proxy to watch when the change is effected. The code measures the delay in two ways: the time taken in milliseconds and the number of ticks (Javascript render loops) elapsed. 

```javascript
// Root element
var app = document.querySelector('#app');

// data
var data = {value: ""};

// Counters
var clickTime = null;
var clickTick = 0;
var currentTick = 0;

// Start counting on click
function startClick() {
  clickTime = performance.now();
  clickTick = currentTick;
}

// Report elapsed time on change
function reportTime() {
  var timeDiff = performance.now() - clickTime;
  var tickDiff = currentTick - clickTick;

  console.log('timeDiff', timeDiff);
  console.log('tickDiff', tickDiff);
}

// Create the button that will use Go to modify a value
var goButton = document.createElement('button');
goButton.appendChild(document.createTextNode("Go"));
goButton.onclick = function (e) {
  startClick();
  Remote.eval('data.value = Math.random().toString();');
}
app.appendChild(goButton);

// Create the button that will use JS to modify the value
var jsButton = document.createElement('button');
jsButton.appendChild(document.createTextNode("Js"));
jsButton.onclick = function(e) {
  startClick();
  data.value = Math.random().toString();
}
app.appendChild(jsButton);

// Watch change in variable
data = new Proxy(data, {
  set: function (target, key, value) {
      target[key] = value;
      if (key === 'value') {
        reportTime();
      }
  }
});

// Count ticks
function tickIncrement() { 
  currentTick++;
  window.setTimeout(tickIncrement, 0);
}
tickIncrement();
```

As expected the Javascript version was instant - the Go version took one tick (always), and between 3 and 6 milliseconds:

|             | Js | Go    |
|-------------|----|-------|
|Milliseconds | 0  | 3 to 6|
|Ticks        | 0  | 1     |


## Test with some work happening in the Javascript loop

Next I was wondering how the results would be affected if the Javascript also did some work on every tick. I updated the code of `tickIncrement` so that it would delete and create a 100 DOM elements every tick:

```javascript
function tickIncrement() {
  var i;
  var prev_iteration = currentTick % 2;
  var next_iteration = (currentTick + 1 ) % 2;

  // Remove old elements
  var old_elements = document.getElementsByClassName('addrem_' + prev_iteration);
  for (i = 0; i < old_elements.length; i++) {
    old_elements[i].parentNode.removeChild(old_elements[i]);
  }
  // Add new elements
  for (i = 0; i < 100; i++) {
    var new_element = document.createElement('div');
    new_element.classList.add('addrem_' + next_iteration);
    new_element.appendChild(document.createTextNode("hello " + next_iteration + " " + i));
    app.appendChild(new_element);
  }

  currentTick++;
  window.setTimeout(tickIncrement, 0);
}
```

The Javascript, as expected, was still instant. The Go version still took one tick, but the time spent was now between 7 and 8 milliseconds.

|             | Js | Go    |
|-------------|----|-------|
|Milliseconds | 0  | 7 to 9|
|Ticks        | 0  | 1     |


What this shows is that it does not matter how long one tick takes - the process of calling a Go method, and having the Go method change a variable in the Javascript (by executing Javascript code) will always take one tick.

## Test with some work happening in the Go callback

I also wanted to see how work happening in the Go callback would affect things. I rewrote `RPC.Eval` to include a small pause:

```go
func (rpc *RPC) Eval(js string) {
    time.Sleep(5 * 1000000)
    view.Eval(js)
}
```

This did not, of course, change anything to the Javascript implementation. The Go implementation now took between 10 and 12 milliseconds, and two 2 ticks. The number of ticks is dependent on the time spent - if I increase the length of the pause, more ticks go by.

|             | Js | Go       |
|-------------|----|----------|
|Milliseconds | 0  | 10 to 12 |
|Ticks        | 0  | 2        |


What this shows is that while the Go invocation is dependent on the length of the tick, the Javascript loop is not delayed by Go.

## Test with some work happening both sides 

If I now combine the two tests - work happening on the Javascript side and on the Go side - I see the time go up, but the number of ticks go down:

|             | Js | Go       |
|-------------|----|----------|
|Milliseconds | 0  | 13 to 15 |
|Ticks        | 0  | 1        |


This is as expected - more work is happening on the Go side, but the tick is longer so it only takes one tick.

## <a name='conclusion'></a> Conclusion

Invoking a Go method from Javascript, and having that Go method change data (by running code) on the Javascript side always takes at least one tick (Javascript loop) - regardless of how long the tick takes. In my measurements this took at least 3 to 5 milliseconds, though these results are likely to vary. The time taken to run the Go code did not slow down or affect the Javascript loop.

When building an application in Go and using webview for the UI, there are broadly three options:

1. Have most of the application logic in Go, while using webview mostly for updating the DOM;
2. Have all the logic related to the user interface in Javascript, and the rest of the application logic in Go;
3. Have most of the application logic in Javascript, while using Go as a thin layer when we need to access the host.

The results show that 1. is not a viable option - a user interface must be as responsive as possible, and we should avoid introducing any unnecessary delays. The delay however is sufficiently small that both options 2. and 3. are viable.
