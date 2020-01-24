# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval
from odoo.tools.misc import split_every
from odoo import _, api, fields, models, registry, SUPERUSER_ID
from odoo.osv import expression
import threading
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class InheritResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    hide_bestregards = fields.Boolean(string="Hide Best Regards")
    hide_header = fields.Boolean(string="Hide Header")
    hide_footer = fields.Boolean(string="Hide Footer")

    @api.model
    def get_values(self):
        classified = self._get_classified_fields()
        print("CLassified", classified['config'])
        for name, icp in classified['config']:
            field = self._fields[name]
            IrConfigParameter = self.env['ir.config_parameter'].sudo()
            value = IrConfigParameter.get_param(icp, field.default(self) if field.default else False)
            print("FIELD", field)
            print("FIELD.default", field.default(self) if field.default else False)
            print("VALUE", value)
            if value is not False:
                if field.type == 'many2one':
                    try:
                        # Special case when value is the id of a deleted record, we do not want to
                        # block the settings screen
                        value = self.env[field.comodel_name].browse(int(value)).exists().id
                        print("VALUEEE", value)
                    except:
                        WARNING_MESSAGE = "Error when converting value %r of field %s for ir.config.parameter %r"
                        _logger.warning(WARNING_MESSAGE, value, field, icp)


        res = super(InheritResConfigSettings, self).get_values()
        res.update(
            hide_bestregards=self.env['ir.config_parameter'].sudo().get_param(
                'remove_mail_closing_extended.hide_bestregards'),
            hide_header=self.env['ir.config_parameter'].sudo().get_param(
                'remove_mail_closing_extended.hide_header'),
            hide_footer=self.env['ir.config_parameter'].sudo().get_param(
                'remove_mail_closing_extended.hide_footer'),
        )
        return res


    def set_values(self):
        super(InheritResConfigSettings, self).set_values()
        param = self.env['ir.config_parameter'].sudo()

        field1 = self.hide_bestregards or False
        field2 = self.hide_header or False
        field3 = self.hide_footer or False

        param.set_param('remove_mail_closing_extended.hide_bestregards', field1)
        param.set_param('remove_mail_closing_extended.hide_header', field2)
        param.set_param('remove_mail_closing_extended.hide_footer', field3)


class MailComposerInherit(models.TransientModel):
    _inherit = 'mail.compose.message'

    def send_mail(self, auto_commit=False):
        """ Process the wizard content and proceed with sending the related
            email(s), rendering any template patterns on the fly if needed. """
        notif_layout = self._context.get('custom_layout')
        # Several custom layouts make use of the model description at rendering, e.g. in the
        # 'View <document>' button. Some models are used for different business concepts, such as
        # 'purchase.order' which is used for a RFQ and and PO. To avoid confusion, we must use a
        # different wording depending on the state of the object.
        # Therefore, we can set the description in the context from the beginning to avoid falling
        # back on the regular display_name retrieved in '_notify_prepare_template_context'.
        model_description = self._context.get('model_description')
        for wizard in self:
            # If 'Hide Best Regards' is selected
            if self.env['ir.config_parameter'].sudo().get_param('remove_mail_closing_extended.hide_bestregards'):
                notif_layout = "remove_mail_closing_extended.mail_notification_paynow_without_best_regards"

            # If 'Hide Header' is selected
            if self.env['ir.config_parameter'].sudo().get_param('remove_mail_closing_extended.hide_header'):
                notif_layout = "remove_mail_closing_extended.mail_notification_paynow_without_header"

            # If 'Hide Footer' is selected
            if self.env['ir.config_parameter'].sudo().get_param('remove_mail_closing_extended.hide_footer'):
                notif_layout = "remove_mail_closing_extended.mail_notification_paynow_without_footer"

            # If 'Hide Best Regards' and 'Hide Header' is selected
            if self.env['ir.config_parameter'].sudo().get_param('remove_mail_closing_extended.hide_bestregards') and self.env['ir.config_parameter'].sudo().get_param('remove_mail_closing_extended.hide_header'):
                notif_layout = "remove_mail_closing_extended.mail_notification_paynow_without_br_and_header"

            # If 'Hide Best Regards' and 'Hide Footer' is selected
            if self.env['ir.config_parameter'].sudo().get_param('remove_mail_closing_extended.hide_bestregards') and self.env['ir.config_parameter'].sudo().get_param('remove_mail_closing_extended.hide_footer'):
                notif_layout = "remove_mail_closing_extended.mail_notification_paynow_without_br_and_footer"

            # If 'Hide Header' and 'Hide Footer' is selected
            if self.env['ir.config_parameter'].sudo().get_param('remove_mail_closing_extended.hide_bestregards') and self.env['ir.config_parameter'].sudo().get_param('remove_mail_closing_extended.hide_footer'):
                notif_layout = "remove_mail_closing_extended.mail_notification_paynow_without_header_and_footer"

            # If all the buttons are checked
            if self.env['ir.config_parameter'].sudo().get_param('remove_mail_closing_extended.hide_bestregards') and self.env['ir.config_parameter'].sudo().get_param('remove_mail_closing_extended.hide_header') and self.env['ir.config_parameter'].sudo().get_param('remove_mail_closing_extended.hide_footer'):
                notif_layout = "remove_mail_closing_extended.mail_notification_paynow_without_br_header_and_footer"





            # Duplicate attachments linked to the email.template.
            # Indeed, basic mail.compose.message wizard duplicates attachments in mass
            # mailing mode. But in 'single post' mode, attachments of an email template
            # also have to be duplicated to avoid changing their ownership.
            if wizard.attachment_ids and wizard.composition_mode != 'mass_mail' and wizard.template_id:
                new_attachment_ids = []
                for attachment in wizard.attachment_ids:
                    if attachment in wizard.template_id.attachment_ids:
                        new_attachment_ids.append(
                            attachment.copy({'res_model': 'mail.compose.message', 'res_id': wizard.id}).id)
                    else:
                        new_attachment_ids.append(attachment.id)
                new_attachment_ids.reverse()
                wizard.write({'attachment_ids': [(6, 0, new_attachment_ids)]})

            # Mass Mailing
            mass_mode = wizard.composition_mode in ('mass_mail', 'mass_post')

            Mail = self.env['mail.mail']
            ActiveModel = self.env[wizard.model] if wizard.model and hasattr(self.env[wizard.model],
                                                                             'message_post') else self.env[
                'mail.thread']
            if wizard.composition_mode == 'mass_post':
                # do not send emails directly but use the queue instead
                # add context key to avoid subscribing the author
                ActiveModel = ActiveModel.with_context(mail_notify_force_send=False, mail_create_nosubscribe=True)
            # wizard works in batch mode: [res_id] or active_ids or active_domain
            if mass_mode and wizard.use_active_domain and wizard.model:
                res_ids = self.env[wizard.model].search(safe_eval(wizard.active_domain)).ids
            elif mass_mode and wizard.model and self._context.get('active_ids'):
                res_ids = self._context['active_ids']
            else:
                res_ids = [wizard.res_id]

            batch_size = int(self.env['ir.config_parameter'].sudo().get_param('mail.batch_size')) or self._batch_size
            sliced_res_ids = [res_ids[i:i + batch_size] for i in range(0, len(res_ids), batch_size)]

            if wizard.composition_mode == 'mass_mail' or wizard.is_log or (
                    wizard.composition_mode == 'mass_post' and not wizard.notify):  # log a note: subtype is False
                subtype_id = False
            elif wizard.subtype_id:
                subtype_id = wizard.subtype_id.id
            else:
                subtype_id = self.env['ir.model.data'].xmlid_to_res_id('mail.mt_comment')

            for res_ids in sliced_res_ids:
                batch_mails = Mail
                all_mail_values = wizard.get_mail_values(res_ids)
                for res_id, mail_values in all_mail_values.items():
                    if wizard.composition_mode == 'mass_mail':
                        batch_mails |= Mail.create(mail_values)
                    else:
                        post_params = dict(
                            message_type=wizard.message_type,
                            subtype_id=subtype_id,
                            email_layout_xmlid=notif_layout,
                            add_sign=not bool(wizard.template_id),
                            mail_auto_delete=wizard.template_id.auto_delete if wizard.template_id else False,
                            model_description=model_description)
                        post_params.update(mail_values)
                        if ActiveModel._name == 'mail.thread':
                            if wizard.model:
                                post_params['model'] = wizard.model
                                post_params['res_id'] = res_id
                            if not ActiveModel.message_notify(**post_params):
                                # if message_notify returns an empty record set, no recipients where found.
                                raise UserError(_("No recipient found."))
                        else:
                            ActiveModel.browse(res_id).message_post(**post_params)

                if wizard.composition_mode == 'mass_mail':
                    batch_mails.send(auto_commit=auto_commit)




