/**
 * Copyright 2017 SYLEAM Info Services
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
**/

odoo.define('microcred_profile.userguide', function (require) {
    "use strict";

    var UserMenu = require('web.UserMenu');

     UserMenu.include({

         on_menu_userguide: function () {
             window.open('https://sites.google.com/a/baobab.bz/odoo/', '_blank');
         }

     });
});

