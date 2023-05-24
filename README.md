# onboarding odoo

Install gimera and wodoo 
```
one time:
pipx install gimera
pipx install wodoo
gimera completion -x
odoo completion -x
<relogin bash>

then for the odoo:
gimera apply    #one time / not often
odoo reload     # more often called
odoo build      # more often called
odoo -f db reset -C  # to reset a db
odoo update     # often called
odoo up -d      # often called
```