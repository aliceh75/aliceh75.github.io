Title: Using modules for workspaces in Go 
Date: 2018-12-01
Slug: using-modules-for-workspaces-in-golang
Tags: go
Summary: As of Go 1.11, the Go programming language has (experimental) <a href="https://golang.org/doc/go1.11#modules">support for modules</a>. This addresses a number of needs - such as ensuring semantic versioning, ensuring reproducible builds, etc. Here I look specifically at how modules help replace the need for `$GOPATH` based workspaces.

As of Go 1.11, the Go programming language has (experimental) <a href="https://golang.org/doc/go1.11#modules">support for modules</a>. This addresses a number of needs - such as ensuring semantic versioning, ensuring reproducible builds, etc. Here I look specifically at how modules help replace the need for `$GOPATH` based workspaces.

In that context a module is simply an isolated collection of packages - as you'd get with a <a href=="https://docs.python.org/3/tutorial/venv.html">Python virtual environment</a>.

With Go 1.11 you create a module by adding a `go.mod` file in a folder outside of your `$GOPATH`. This file can be created automatically by running `go mod init`:

```
$ mkdir myexample
$ cd myexample
$ go mod init myexample
```

Once you've done that, when you run a go command in folder beneath `myexample`, go will use the place where the `go.mod` file is a your project root. You should place your `main` package in the project root, and can place other packages in their own folder. Packages are then imported using `myexample/packagename`. So if you had the following file in `myexample/greetings/hello.go`:

```go
package greetings

func hello() {
  return "Hello World"
}
```

You could then import the `greetings` package from, say `myexample/main.go` as `myexample/greetings`:

```go
package main

import (
  "fmt"
  "myexample/greetings"
)

func main() {
  fmt.PrintLn(greetings.hello())
}
```

And you can then run the code by executing (from within the `myexample` folder hierarchy):

```
$ go run myexample
```

There is a lot more to modules than enabling workspaces - I suggest you look at the <a href="https://github.com/golang/go/wiki/Modules">Go Modules Wiki</a> for more information on modules, in particular how they replace other forms of dependency management.
