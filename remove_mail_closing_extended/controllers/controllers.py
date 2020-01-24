# -*- coding: utf-8 -*-
# from odoo import http


# class CustomAddons/removeMailClosingExtended(http.Controller):
#     @http.route('/custom_addons/remove_mail_closing_extended/custom_addons/remove_mail_closing_extended/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_addons/remove_mail_closing_extended/custom_addons/remove_mail_closing_extended/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_addons/remove_mail_closing_extended.listing', {
#             'root': '/custom_addons/remove_mail_closing_extended/custom_addons/remove_mail_closing_extended',
#             'objects': http.request.env['custom_addons/remove_mail_closing_extended.custom_addons/remove_mail_closing_extended'].search([]),
#         })

#     @http.route('/custom_addons/remove_mail_closing_extended/custom_addons/remove_mail_closing_extended/objects/<model("custom_addons/remove_mail_closing_extended.custom_addons/remove_mail_closing_extended"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_addons/remove_mail_closing_extended.object', {
#             'object': obj
#         })
