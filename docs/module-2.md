# Module 2: Declarative BGP & Jinja2

Render per-vendor BGP configuration from a single data model.

=== "FRRouting (vtysh)"

    ```ini
    router bgp 65000
      neighbor 10.0.0.1 remote-as 65001
      neighbor 10.0.0.3 remote-as 65002
    ```

=== "Nokia SR Linux (YANG/JSON)"

    ```json
    {
      "network-instance": [{
        "name": "default",
        "protocols": {
          "bgp": { "autonomous-system": 65001 }
        }
      }]
    }
    ```

!!! warning
    Placeholder values above; replace them with the workshop's actual addressing.
