=============================
Scheduled Asynchronous Export
=============================

.. 
   !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   !! This file is generated by oca-gen-addon-readme !!
   !! changes will be overwritten.                   !!
   !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   !! source digest: sha256:cd38991773bdacb7c48929d6e50f66c3b75b7eeb11908482511d1d2d44e4e231
   !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

.. |badge1| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
    :target: https://odoo-community.org/page/development-status
    :alt: Beta
.. |badge2| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3
.. |badge3| image:: https://img.shields.io/badge/github-OCA%2Fqueue-lightgray.png?logo=github
    :target: https://github.com/OCA/queue/tree/14.0/export_async_schedule
    :alt: OCA/queue
.. |badge4| image:: https://img.shields.io/badge/weblate-Translate%20me-F47D42.png
    :target: https://translation.odoo-community.org/projects/queue-14-0/queue-14-0-export_async_schedule
    :alt: Translate me on Weblate
.. |badge5| image:: https://img.shields.io/badge/runboat-Try%20me-875A7B.png
    :target: https://runboat.odoo-community.org/builds?repo=OCA/queue&target_branch=14.0
    :alt: Try me on Runboat

|badge1| |badge2| |badge3| |badge4| |badge5|

Add a new Automation feature: Scheduled Exports.
Based on an export list and a domain, an email is sent every X
hours/days/weeks/months to a selection of users.

**Table of contents**

.. contents::
   :local:

Configuration
=============

The configuration of a scheduled export is based on export lists.

To create an export list:

* open the list view of the model to export
* select at least one record, and open "Action → Export"
* select the fields to export and save using "Save fields list".

To configure a scheduled export:

* open "Settings → Technical → Automation → Scheduled Exports"
* create a scheduled export by filling the form

A Scheduled Action named "Send Scheduled Exports" checks every hour
if Scheduled Exports have to be executed.

Usage
=====

When the configuration of a Scheduled Export is done, their execution
is automatic.

Users will receive an email containing a link to download the exported file at
the specified frequency. The attachments stay in the database for 7 days by
default (it can be changed with the system parameter ``attachment.ttl``.

Known issues / Roadmap
======================

* We could configure a custom TTL (time-to-live) for each scheduled export

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/queue/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us to smash it by providing a detailed and welcomed
`feedback <https://github.com/OCA/queue/issues/new?body=module:%20export_async_schedule%0Aversion:%2014.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.

Do not contact contributors directly about support or help with technical issues.

Credits
=======

Authors
~~~~~~~

* Camptocamp

Contributors
~~~~~~~~~~~~

* Guewen Baconnier (Camptocamp)
* `Komit <https://komit-consulting.com>`_:

  * Cuong Nguyen Mtm <cuong.nmtm@komit-consulting.com>

Other credits
~~~~~~~~~~~~~

The migration of this module from 13.0 to 14.0 was financially supported by:

- Scaleway SAS (https://www.scaleway.com/)
- Komit (https://komit-consulting.com)

Maintainers
~~~~~~~~~~~

This module is maintained by the OCA.

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

.. |maintainer-guewen| image:: https://github.com/guewen.png?size=40px
    :target: https://github.com/guewen
    :alt: guewen

Current `maintainer <https://odoo-community.org/page/maintainer-role>`__:

|maintainer-guewen| 

This module is part of the `OCA/queue <https://github.com/OCA/queue/tree/14.0/export_async_schedule>`_ project on GitHub.

You are welcome to contribute. To learn how please visit https://odoo-community.org/page/Contribute.
