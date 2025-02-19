==================================
Confirm/Alert pop-up before saving
==================================

.. 
   !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   !! This file is generated by oca-gen-addon-readme !!
   !! changes will be overwritten.                   !!
   !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   !! source digest: sha256:7ffe943eb22ee465e35d6e7d5eeca244b46c04ac4b25c62a1afc5c214fa80ca9
   !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

.. |badge1| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
    :target: https://odoo-community.org/page/development-status
    :alt: Beta
.. |badge2| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3
.. |badge3| image:: https://img.shields.io/badge/github-OCA%2Fweb-lightgray.png?logo=github
    :target: https://github.com/OCA/web/tree/14.0/web_create_write_confirm
    :alt: OCA/web
.. |badge4| image:: https://img.shields.io/badge/weblate-Translate%20me-F47D42.png
    :target: https://translation.odoo-community.org/projects/web-14-0/web-14-0-web_create_write_confirm
    :alt: Translate me on Weblate
.. |badge5| image:: https://img.shields.io/badge/runboat-Try%20me-875A7B.png
    :target: https://runboat.odoo-community.org/builds?repo=OCA/web&target_branch=14.0
    :alt: Try me on Runboat

|badge1| |badge2| |badge3| |badge4| |badge5|

This module provides feature to create custom confirmation or alert dialog when user creates or writes record.
Module includes only methods that you can use in your code. That means programming is always required.
See usage section for more information.

**Table of contents**

.. contents::
   :local:

Usage
=====

Create popup.message record. Specify model_id, field_ids (which fields will trigger alert) and other fields.
Put you code into **get_message_informations** or **execute_processing** method of you model.
Return dict (perform read() to get it).
Here is some examples how you can use this module features in your code.

Confirm res.partner change:

..  code-block:: python

    msg = self.env['popup.message'].create(
        {
            'model_id': self.env['ir.model'].search([('model', '=', 'res.partner')]).id,
            'field_ids': [(6, 0, self.env['ir.model.fields'].search([('model', '=', 'res.partner')]).ids)],
            'popup_type': 'confirm',
            'title': 'Warning',
            'message': 'Are you sure want to update record?',
        }
    )
    return msg.read()

Sale order alert:

..  code-block:: python

    msg = self.env['popup.message'].create(
        {
            'model_id': self.env['ir.model'].search([('model', '=', 'sale.order')]).id,
            'field_ids': [(6, 0, self.env['ir.model.fields'].search([('model', '=', 'sale.order')]).ids)],
            'popup_type': 'alert',
            'title': 'Attention',
            'message': 'Sale order was updated.',
        }
    )
    return msg.read()

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/web/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us to smash it by providing a detailed and welcomed
`feedback <https://github.com/OCA/web/issues/new?body=module:%20web_create_write_confirm%0Aversion:%2014.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.

Do not contact contributors directly about support or help with technical issues.

Credits
=======

Authors
~~~~~~~

* Smile

Contributors
~~~~~~~~~~~~

* `Smile <https://www.smile.eu/en>`_


* `Ooops404 <https://www.ooops404.com>`__:

  * Ilyas <irazor147@gmail.com>

Maintainers
~~~~~~~~~~~

This module is maintained by the OCA.

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

This module is part of the `OCA/web <https://github.com/OCA/web/tree/14.0/web_create_write_confirm>`_ project on GitHub.

You are welcome to contribute. To learn how please visit https://odoo-community.org/page/Contribute.
