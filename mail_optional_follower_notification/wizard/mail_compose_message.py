# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    notify_followers = fields.Boolean(default=True)

    #@api.multi
    def action_send_mail(self, auto_commit=False):
        ctx = self.env.context.copy()
        for wizard in self:
            print("wizard %s" %wizard.partner_ids)
            ctx['notify_followers'] = wizard.notify_followers
            wizard.partner_ids = []
            wizard = wizard.with_context(ctx)
            super(MailComposeMessage, wizard).action_send_mail(
                )
        return {'type': 'ir.actions.act_window_close'}



    def get_mail_values(self, res_ids):
        """Generate the values that will be used by send_mail to create mail_messages
        or mail_mails. """
        self.ensure_one()
        results = dict.fromkeys(res_ids, False)
        rendered_values = {}
        mass_mail_mode = self.composition_mode == 'mass_mail'

        # render all template-based value at once
        if mass_mail_mode and self.model:
            rendered_values = self.render_message(res_ids)
        # compute alias-based reply-to in batch
        reply_to_value = dict.fromkeys(res_ids, None)
        if mass_mail_mode and not self.no_auto_thread:
            records = self.env[self.model].browse(res_ids)
            reply_to_value = self.env['mail.thread']._notify_get_reply_to_on_records(default=self.email_from, records=records)

        blacklisted_rec_ids = []
        if mass_mail_mode and issubclass(type(self.env[self.model]), self.pool['mail.thread.blacklist']):
            BL_sudo = self.env['mail.blacklist'].sudo()
            blacklist = set(BL_sudo.search([]).mapped('email'))
            if blacklist:
                targets = self.env[self.model].browse(res_ids).read(['email_normalized'])
                # First extract email from recipient before comparing with blacklist
                blacklisted_rec_ids.extend([target['id'] for target in targets
                                            if target['email_normalized'] and target['email_normalized'] in blacklist])

        for res_id in res_ids:
            _logger.info("RES ID: %s" %res_id)
            # static wizard (mail.message) values

            
            if self.notify_followers:
                mail_values = {
                'subject': self.subject,
                'body': self.body or '',
                'parent_id': self.parent_id and self.parent_id.id,
                'partner_ids': [partner.id for partner in self.partner_ids],
                'attachment_ids': [attach.id for attach in self.attachment_ids],
                'author_id': self.author_id.id,
                'email_from': self.email_from,
                'record_name': self.record_name,
                'no_auto_thread': self.no_auto_thread,
                'mail_server_id': self.mail_server_id.id,
                'mail_activity_type_id': self.mail_activity_type_id.id,
                'notify_followers' : self.notify_followers,
                }
            else:


                mail_values = {
                    'subject': self.subject,
                    'body': self.body or '',
                    'parent_id': self.parent_id and self.parent_id.id,
                    'partner_ids': [partner.id for partner in self.partner_ids],
                    'attachment_ids': [attach.id for attach in self.attachment_ids],
                    'author_id': self.author_id.id,
                    'email_from': self.email_from,
                    'record_name': self.record_name,
                    'no_auto_thread':'null',
                    'mail_server_id': self.mail_server_id.id,
                    'mail_activity_type_id': self.mail_activity_type_id.id,
                    'notify_followers' : self.notify_followers,
                }

            # mass mailing: rendering override wizard static values
            if mass_mail_mode and self.model:
                record = self.env[self.model].browse(res_id)
                mail_values['headers'] = record._notify_email_headers()
                # keep a copy unless specifically requested, reset record name (avoid browsing records)
                mail_values.update(notification=not self.auto_delete_message, model=self.model, res_id=res_id, record_name=False)
                # auto deletion of mail_mail
                if self.auto_delete or self.template_id.auto_delete:
                    mail_values['auto_delete'] = True
                # rendered values using template
                email_dict = rendered_values[res_id]
                mail_values['partner_ids'] += email_dict.pop('partner_ids', [])
                mail_values.update(email_dict)
                if not self.no_auto_thread:
                    mail_values.pop('reply_to')
                    if reply_to_value.get(res_id):
                        mail_values['reply_to'] = reply_to_value[res_id]
                if self.no_auto_thread and not mail_values.get('reply_to'):
                    mail_values['reply_to'] = mail_values['email_from']
                # mail_mail values: body -> body_html, partner_ids -> recipient_ids
                mail_values['body_html'] = mail_values.get('body', '')
                mail_values['recipient_ids'] = [(4, id) for id in mail_values.pop('partner_ids', [])]

                # process attachments: should not be encoded before being processed by message_post / mail_mail create
                mail_values['attachments'] = [(name, base64.b64decode(enc_cont)) for name, enc_cont in email_dict.pop('attachments', list())]
                attachment_ids = []
                for attach_id in mail_values.pop('attachment_ids'):
                    new_attach_id = self.env['ir.attachment'].browse(attach_id).copy({'res_model': self._name, 'res_id': self.id})
                    attachment_ids.append(new_attach_id.id)
                attachment_ids.reverse()
                mail_values['attachment_ids'] = self.env['mail.thread']._message_post_process_attachments(
                    mail_values.pop('attachments', []),
                    attachment_ids,
                    {'model': 'mail.message', 'res_id': 0}
                )['attachment_ids']
                # Filter out the blacklisted records by setting the mail state to cancel -> Used for Mass Mailing stats
                if res_id in blacklisted_rec_ids:
                    mail_values['state'] = 'cancel'
                    # Do not post the mail into the recipient's chatter
                    mail_values['notification'] = False


            results[res_id] = mail_values
        return results
