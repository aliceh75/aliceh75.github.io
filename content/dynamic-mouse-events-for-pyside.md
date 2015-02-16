Title: Dynamic mouse events for PySide
Date: 2014-09-29
Slug: dynamic-mouse-events-for-pyside
Tags: python, pyside
Summary: [PySide](http://qt-project.org/wiki/PySide), one of the Python bindings for [Qt](http://qt-project.org/), uses the same event model as the C++ version of Qt - one that is designed for static languages. Here I show how to implement a layer above PySide's mouse events that provides a more dynamic event model.

A static event model
--------------------

[PySide](http://qt-project.org/wiki/PySide), one of the Python bindings for [Qt](http://qt-project.org/), uses the same event model as the C++ version of Qt - one that is designed for static languages. The problem with this event model is that the semantic of your code is defined by the event. For example if you want to pan a view when the middle button is clicked, you would have to implement `mousePressEvent`, `mouseReleaveEvent` and `mouseMoveEvent` in this way:

    :::python
    class MyView(QtGui.QGraphicsView):
        def __init__(self, parent=None):
            QtGui.QGraphicsView.__init__(self, parent)
            self._mouse_press = None

        def mousePressEvent(self, event):
            if event.button() == QtCore.Qt.MidButton:
              self._middle_press = (event.pos().x(), event.pos().y())

        def mouseReleaseEvent(self, event):
            self._middle_press = None

        def mouseMoveEvent(self, event):
            if self._middle_press is not None:
                pos = (event.pos().x(), event.pos().y())
                delta_x = pos[0] - self._middle_press[0]
                delta_y = pos[1] - self._middle_press[1]
                h = self.horizontalScrollBar()
                v = self.verticalScrollBar()
                h.setValue(h.value() + delta_x)
                v.setValue(v.value() + delta_y)
                self._middle_press = pos

This could be implemented in various different ways, but the one thing that remains is that we must spread the logic between three calls, `mousePressEvent`, `mouseReleaseEvent` and `mouseMoveEvent`, which are named after the event being triggered, not after what the functionality actually does. This means that there is no way to tell what happens without reading the whole code line by line.

Implementing a more dynamic model
---------------------------------

What we want, instead of implementing something called `mouseMoveEvent` is to implement something called `scroll_view` - after what it does, not the way it was invoked - and get that called, with the position delta, when the mouse is moved with the middle button down. Something like this:

    :::python
    add_mouse_handler(
        event={
            'event': 'move',
            'button': 'middle'
        },
        callback=self.scroll_view,
        args=[MouseState('delta_x'), MouseState('delta_y')]
    )

What this does is self-explanatory: when the mouse is moved with the middle button pressed, invoke `self.scroll_view` with the mouse position delta. Now our class only needs to implement one method, `scroll_view`, named after what it actually does, and is invoked with meaninful parameters.

The full class so implemented would look like:

    :::python
    class MyView(MouseHandler, QtGui.QGraphicsView):
        def __init__(self, parent=None):
            QtGui.QGraphicsView.__init__(self, parent)
            MouseHandler.__init__(self, parent_class=QtGui.QGraphicsView)
            self.add_mouse_handler(
                event={
                    'event': 'move',
                    'button': 'middle'
                },
                callback=self.scroll_view,
                args=[MouseState('delta_x'), MouseState('delta_y')]
            )

        def scroll_view(self, delta_x, delta_y):
            h = self.horizontalScrollBar()
            v = self.verticalScrollBar()
            h.setValue(h.value() + delta_x)
            v.setValue(v.value() + delta_y)

It's not just much shorter - it's also much clearer. None of the actual business logic was moved out, `scroll_view` is generic and re-usable, and the `add_mouse_handler` call can be understood without knowing the underlying library.

The mouse state
----------------
The `MouseHandler` mixin works by keeping a comprehensive state of the mouse, which includes:

- The event name ('press', 'release', 'double-click', 'wheel', 'move', 'enter' or 'leave');
- The current position of the mouse;
- The delta of the mouse movement;
- The currently pressed button;
- The mouse position at which the button was pressed;
- The delta value of the wheel move;
- Whether the mouse is over the current element (for 'hover' events);
- Which keyboard modfiers are currently pressed.

The `MouseHandler` makes it possible to react to any combination of values in the mouse state - for example when the mouse is being moved with the middle button down and the control key pressed. And the handler being called can be passed a list of arguments, any of which may come from the mouse state - so we can pass the mouse co-ordinates, the mouse delta, etc. This can be combined with static arguments - so if our `scroll_view` method had a last argument called `relative` and defaulting to False, we could have set the argument list to
`[MouseState('delta_x'), MouseState('delta_y'), True]`

To increase the expressiveness of the code, classes can event add their own custom mouse states - for instance you could add `pressed_corner` to define which corner of a box was pressed. You can then fire different move events depending on this.

The code!
---------

At this stage I'm not sure whether I'll support this in the long term - that depends on whether I get involved in more PySide projects. For now, I will share the code here - I might create a repo at some point (check my GitHub page). Note that the code is shared as-is for inspiration, rather than something you can just pull and re-use. Here goes:

    :::python
    from PySide import QtCore
    
    
    class MouseState(object):
        """Class used to represent a property of a mouse state.
    
        This is used to represent callback arguments that must be defined when the event is fired - eg. MouseState('x')
        will represent the 'x' property of the mouse state when the event is fired
    
        Parameters
        ----------
        state : str
            The mouse state to represent
    
        Attributes
        ----------
        state : str
            The mouse state to represent
        """
        def __init__(self, state):
            self.state = state
    
    
    class MouseHandler(object):
        """Mixin used to map mouse events to methods.
    
        This mixin uses the following event names: 'press', 'release', 'double-click', 'wheel', 'move', 'enter', 'leave'.
        The mouse state contains the following properties:
            event : str
                The event name
            x : int
                Current X mouse position
            y : int
                Current Y mouse position
            button : str, None
                The current button state. One of 'left', 'right', 'middle', None
            pressed_x : int, None
                The X coordinate where the mouse was pressed (if applicable) or None
            pressed_y : int, None
                The Y coordinate where the mouse was pressed (if applicable) or None
            delta_x : int
                The X delta of the mouse movement
            delta_y : int
                The Y delta of the mouse movement
            wheel_delta : int
                The delta sent by the mouse wheel on wheel events or None
            over : bool
                True if the mouse is over the current item, false if not
            modifier : int
                A Qt key modifier constant
    
        Example
        -------
        To use MouseEvents, you need to inherit from it and call it's initializer specifying the class which holds
        the default Mouse events implementation:
    
            class GraphicsView(MouseEvents, QtGui.QGraphicsView):
            def __init__(self, parent=None):
                QtGui.QGraphicsView.__init__(self, parent)
                MouseEvents.__init__(self, parent_class=QtGui.QGraphicsView)
    
        You can then add handlers for any combination of events and mouse state:
    
                self.add_mouse_handler({
                    'event': 'move',
                    'button': 'middle'
                }), self.scroll_view, args=[MouseState('x'), MouseState('y'), True])
                self.add_mouse_handler({
                    'event': 'wheel',
                    'button': None,
                    'modifier': QtCore.Qt.ControlModifier
                }, self.zoom)
    
    
        The functions will be called with event-specific arguments:
            def scroll_view(self, x, y, refresh=False):
                h = self.horizontalScrollBar()
                v = self.verticalScrollBar()
                delta = self.get_mouse_state('delta')
                h.setValue(h.value() + delta[0])
                v.setValue(v.value() + delta[1])
    
        Notes
        -----
        - The mixin implements Qt mouse events methods, so classes should not implement their own.
        - Some elements, such as elements derived from QtGraphicsItem, will not trigger mouse move
          events unless a button is pressed. To change that behaviour, you need to call
          `setAcceptHoverEvents` to True. Qt will then fire different events whether a button is
          pressed or not. The MouseEvents abstracts this behaviour - so you can rely on the event
          {'event': 'move', 'over': True} to work in both instances.
        """
        def __init__(self, parent_class):
            self.parent_class = parent_class
    
            self._last_position = (0, 0)
            self._mouse_state = {
                'event': None,
                'button': None,
                'x': 0,
                'y': 0,
                'pressed_x': None,
                'pressed_y': None,
                'delta_x': 0,
                'delta_y': 0,
                'over': False,
                'modifier': QtCore.Qt.NoModifier
            }
    
            self._handlers = {}
    
        def add_mouse_handler(self, event, callback, delegate=False, args=None):
            """Add a new mouse handler
    
            Parameters
            ----------
            event : str, object
                see `_get_event`
            callback : function
                Function to call on event. If delegate is True, the function should return True to
                allow the event to propagate, False otherwise.
            delegate : bool
                If False (the default), events will not propagate when the handler is invoked.
                If True, the value of the callback function will determine whether events should
                propagate (True to propagate)
            args : list, None
                Additional arguments will be passed to the callback methods. Arguments that are
                instances of MouseState will be set to the given mouse state when the event is fired.
            """
            (event, state) = self._get_event(event)
            if args is None:
                args = []
            if event not in self._handlers:
                self._handlers[event] = []
            self._handlers[event].append((callback, state, delegate, args))
    
        def get_mouse_state(self, prop=None):
            """Return the mouse state
    
            Parameters
            ----------
            prop : str, None
                The name of a property or None
    
            Returns
            -------
            object
                Either a given property (if prop is not None), or the whole mouse state object
            """
            if prop is None:
                return self._mouse_state
            else:
                return self._mouse_state[prop]
    
        def set_mouse_state(self, prop, value):
            """Set a mouse state value
    
            This may be called to set custom mouse state values. It can also be
            used to override existing mouse state values, though those may get
            overwritten at the next update.
    
            Parameters
            ----------
            prop : str
                The name of a property
            value : object
                The value to set
            """
            self._mouse_state[prop] = value
    
        def _get_event(self, event):
            """Return a (event, state) tuple for the given event
    
            Parameters
            ----------
            event : str, dictionary
                May be an event name, or a dictionary mapping 'event' and any other mouse_state properties to values.
    
            Returns
            -------
            tuple
                An (event, state) tuple
            """
            event_str = event
            state = {}
            if isinstance(event, dict):
                event_str = event['event']
                state = event
                if 'modifier' in state:
                    state['modifier'] = int(state['modifier'])
    
            return event_str, state
    
        def _handle_event(self, event, event_name, default_callback):
            """Handle an event by calling appropriate handlers
    
            Parameters
            ----------
            event : QtEvent
                The event that triggered the call
            event_name : str
                Event name. See `_get_event`
            default_callback : function
                Function to call for propagation
            """
            # Get handlers
            try:
                handlers = self._handlers[event_name]
            except KeyError:
                default_callback(self, event)
                return
            # Set non-event specific mouse state
            self._mouse_state['event'] = event_name
            self._mouse_state['modifier'] = int(event.modifiers())
            self._mouse_state['x'] = event.pos().x()
            self._mouse_state['y'] = event.pos().y()
            self._mouse_state['delta_x'] = self._last_position[0] - self._mouse_state['x']
            self._mouse_state['delta_y'] = self._last_position[1] - self._mouse_state['y']
            self._last_position = (self._mouse_state['x'], self._mouse_state['y'])
            # Call handlers that match the state
            propagate = True
            for (callback, state, delegate, handler_args) in handlers:
                cancel = False
                for prop in state:
                    if self._mouse_state[prop] != state[prop]:
                        cancel = True
                        break
                if cancel:
                    continue
                args = []
                for a in handler_args:
                    if isinstance(a, MouseState):
                        args.append(self.get_mouse_state(a.state))
                    else:
                        args.append(a)
                r = callback(*args)
                if delegate:
                    propagate = propagate & r
                else:
                    propagate = False
            # Propagate or accept the event
            if propagate:
                default_callback(self, event)
            else:
                event.accept()
    
        def mousePressEvent(self, event):
            """Handle mouse press events
    
            Parameters
            ----------
            event : QtEvent
            """
            button_map = {
                QtCore.Qt.MidButton: 'middle',
                QtCore.Qt.LeftButton: 'left',
                QtCore.Qt.RightButton: 'right'
            }
            self._mouse_state['pressed_x'] = event.pos().x()
            self._mouse_state['pressed_y'] = event.pos().y()
            self._mouse_state['button'] = button_map[event.button()]
    
            self._handle_event(event, 'press', self.parent_class.mousePressEvent)
    
        def mouseMoveEvent(self, event):
            """Handle mouse move events
    
            Parameters
            ----------
            event : QtEvent
            """
            self._handle_event(event, 'move', self.parent_class.mouseMoveEvent)
    
        def mouseReleaseEvent(self, event):
            """Handle mouse release events
    
            Parameters
            ----------
            event : QtEvent
            """
            self._handle_event(event, 'release', self.parent_class.mouseReleaseEvent)
            self._mouse_state['button'] = None
            self._mouse_state['pressed_at'] = None
    
        def mouseDoubleClickEvent(self, event):
            """Handle mouse double click events
    
            Parameters
            ----------
            event : QtEvent
            """
            self._handle_event(event, 'double-click', self.parent_class.mouseDoubleClickEvent)
    
        def hoverEnterEvent(self, event):
            """Handle mouse hover enter events
    
            Parameters
            ----------
            event : QtEvent
            """
            self._mouse_state['over'] = True
            self._handle_event(event, 'enter', self.parent_class.hoverEnterEvent)
    
        def hoverMoveEvent(self, event):
            """Handle hoverMoveEvent
    
            Parameters
            ----------
            event : QtEvent
            """
            over = self._mouse_state['over']
            self._mouse_state['over'] = True
            self._handle_event(event, 'move', self.parent_class.hoverMoveEvent)
            self._mouse_state['over'] = over
    
        def hoverLeaveEvent(self, event):
            """Handle mouse hover enter events
    
            Parameters
            ----------
            event : QtEvent
            """
            self._mouse_state['over'] = False
            self._handle_event(event, 'leave', self.parent_class.hoverLeaveEvent)
    
        def wheelEvent(self, event):
            """Handle mouse hover enter events
    
            Parameters
            ----------
            event : QtEvent
            """
            self._mouse_state['wheel_delta'] = event.delta()
            self._handle_event(event, 'wheel', self.parent_class.wheelEvent)
            self._mouse_state['wheel_delta'] = None

It is fairly straightforward to write something similar for keyboard events.
