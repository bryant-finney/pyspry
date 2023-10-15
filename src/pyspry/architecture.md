# Architecture

The following diagram shows the dependencies between classes defined in `pyspry.base`. Additionally,
references to external constructs (i.e. files and environment variables) are shown.

```mermaid
flowchart BT
    A[<code><pre>pyspry.settings</pre></code>] ------>|Import and bootstrap| B(<code><pre>SettingsContainer</pre></code>)
    B --->|Executes| C(<code><pre>ConfigLoader</pre></code>)
    C ----->|Instantiates| E[<code><pre>Settings</pre></code>]
    E --->|Internal storage| F[<code><pre>NestedDict</pre></code>]
    E ----->|Proxied by...| B

    subgraph files
        G((<code>config-0.yaml</code>))
        H((<code>config-1.yaml</code>))
        I((<code><pre>...</pre></code>))
    end
    files -...->|Populates| E

    subgraph environment
        J><code><pre>PREFIX_VAR_0</pre></code>]
        K><code><pre>...</pre></code>]
    end
    environment -..->|Overrides| E

classDef default fill-opacity:0
```
