# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, api
import logging
_logger = logging.getLogger(__name__)

class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model
    def create(self, values):
        ctx = self.env.context.copy()
        #print("context: %s values %s" %(ctx,values))
        if not ctx.get('notify_followers') and values.get('partner_ids'):
            
            partner_list = self.resolve_2many_commands(
                'partner_ids', values.get('partner_ids'), fields=['id'])
            ctx['force_partners_to_notify'] =  [d['id'] for d in partner_list]
        
        return super(MailMessage, self.with_context(ctx)).create(values)

    #@api.multi
    def _notify(self, record, msg_vals, force_send=False,
                send_after_commit=True, model_description=False,
                mail_auto_delete=True):
        
        res = super()._notify(
            record, msg_vals, force_send=force_send,
            send_after_commit=send_after_commit,
            model_description=model_description,
            mail_auto_delete=mail_auto_delete)
        if self.env.context.get('force_partners_to_notify'):
            # Needaction only for recipients
            self.needaction_partner_ids = [
                (6, 0, self.env.context.get('force_partners_to_notify'))]
        return res

class MailMessageThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        """ Main notification method. This method basically does two things

         * call ``_notify_compute_recipients`` that computes recipients to
           notify based on message record or message creation values if given
           (to optimize performance if we already have data computed);
         * performs the notification process by calling the various notification
           methods implemented;

        This method cnn be overridden to intercept and postpone notification
        mechanism like mail.channel moderation.

        :param message: mail.message record to notify;
        :param msg_vals: dictionary of values used to create the message. If given
          it is used instead of accessing ``self`` to lessen query count in some
          simple cases where no notification is actually required;

        Kwargs allow to pass various parameters that are given to sub notification
        methods. See those methods for more details about the additional parameters.
        Parameters used for email-style notifications
        """
        msg_vals = msg_vals if msg_vals else {}
        #_logger.info("MSG VAAALS %s " %msg_vals)
        rdata = self._notify_compute_recipients(message, msg_vals)
        if not rdata:
            return False

        message_values = {}

        if rdata['channels']:
            message_values['channel_ids'] = [(6, 0, [r['id'] for r in rdata['channels']])]
        true_partners = []
        self._notify_record_by_inbox(message, rdata, msg_vals=msg_vals, **kwargs)
        if 'no_auto_thread' in msg_vals and msg_vals['no_auto_thread']=='null':
            so = self.env['sale.order'].search([('id','=',msg_vals['res_id'])])
            true_partner = so.partner_id.id
            for i in rdata['partners']:
                if i['id'] == true_partner:
                    true_partners.append(i)

            rdata['partners'] = true_partners

        self._notify_record_by_email(message, rdata, msg_vals=msg_vals, **kwargs)

        return rdata


