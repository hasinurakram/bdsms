"""
SMS Service Module

Supports multiple SMS providers:
1. Twilio (International)
2. BulkSMS Bangladesh
3. SSL Wireless (Bangladesh)
4. Custom API

Configure in settings.py:
SMS_PROVIDER = 'twilio' or 'bulksms' or 'ssl_wireless' or 'custom'
SMS_API_KEY = 'your_api_key'
SMS_API_SECRET = 'your_api_secret'
SMS_SENDER_ID = 'your_sender_id'
"""

from django.conf import settings
import requests
import logging

logger = logging.getLogger(__name__)


class SMSService:
    """Base SMS Service Class"""
    
    def __init__(self):
        self.provider = getattr(settings, 'SMS_PROVIDER', 'console')
        self.api_key = getattr(settings, 'SMS_API_KEY', '')
        self.api_secret = getattr(settings, 'SMS_API_SECRET', '')
        self.sender_id = getattr(settings, 'SMS_SENDER_ID', 'School')
    
    def send_sms(self, phone_number, message):
        """Send SMS based on configured provider"""
        
        if not phone_number:
            logger.error("No phone number provided")
            return False, "No phone number provided"
        
        if not message:
            logger.error("No message provided")
            return False, "No message provided"
        
        # Remove spaces and format phone number
        phone_number = phone_number.replace(' ', '').replace('-', '')
        
        # Route to appropriate provider
        if self.provider == 'twilio':
            return self._send_via_twilio(phone_number, message)
        elif self.provider == 'bulksms':
            return self._send_via_bulksms(phone_number, message)
        elif self.provider == 'ssl_wireless':
            return self._send_via_ssl_wireless(phone_number, message)
        elif self.provider == 'custom':
            return self._send_via_custom_api(phone_number, message)
        else:
            # Console mode for development
            return self._send_via_console(phone_number, message)
    
    def _send_via_twilio(self, phone_number, message):
        """Send SMS via Twilio"""
        try:
            from twilio.rest import Client
            
            account_sid = self.api_key
            auth_token = self.api_secret
            from_number = self.sender_id
            
            client = Client(account_sid, auth_token)
            
            sms = client.messages.create(
                body=message,
                from_=from_number,
                to=phone_number
            )
            
            logger.info(f"SMS sent via Twilio to {phone_number}: {sms.sid}")
            return True, f"SMS sent successfully (SID: {sms.sid})"
            
        except Exception as e:
            logger.error(f"Twilio SMS error: {str(e)}")
            return False, f"Failed to send SMS: {str(e)}"
    
    def _send_via_bulksms(self, phone_number, message):
        """Send SMS via BulkSMS Bangladesh"""
        try:
            url = "http://bulksmsbd.net/api/smsapi"
            
            params = {
                'api_key': self.api_key,
                'type': 'text',
                'number': phone_number,
                'senderid': self.sender_id,
                'message': message
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('response_code') == 202:
                    logger.info(f"SMS sent via BulkSMS to {phone_number}")
                    return True, "SMS sent successfully"
                else:
                    logger.error(f"BulkSMS error: {result}")
                    return False, f"Failed: {result.get('error_message', 'Unknown error')}"
            else:
                logger.error(f"BulkSMS HTTP error: {response.status_code}")
                return False, f"HTTP Error: {response.status_code}"
                
        except Exception as e:
            logger.error(f"BulkSMS error: {str(e)}")
            return False, f"Failed to send SMS: {str(e)}"
    
    def _send_via_ssl_wireless(self, phone_number, message):
        """Send SMS via SSL Wireless Bangladesh"""
        try:
            url = "https://smsplus.sslwireless.com/api/v3/send-sms"
            
            payload = {
                'api_token': self.api_key,
                'sid': self.sender_id,
                'msisdn': phone_number,
                'sms': message,
                'csms_id': ''
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'SUCCESS':
                    logger.info(f"SMS sent via SSL Wireless to {phone_number}")
                    return True, "SMS sent successfully"
                else:
                    logger.error(f"SSL Wireless error: {result}")
                    return False, f"Failed: {result.get('message', 'Unknown error')}"
            else:
                logger.error(f"SSL Wireless HTTP error: {response.status_code}")
                return False, f"HTTP Error: {response.status_code}"
                
        except Exception as e:
            logger.error(f"SSL Wireless error: {str(e)}")
            return False, f"Failed to send SMS: {str(e)}"
    
    def _send_via_custom_api(self, phone_number, message):
        """Send SMS via custom API"""
        try:
            # Implement your custom API here
            url = getattr(settings, 'SMS_CUSTOM_API_URL', '')
            
            if not url:
                return False, "Custom API URL not configured"
            
            # Customize this based on your API
            payload = {
                'api_key': self.api_key,
                'phone': phone_number,
                'message': message,
                'sender': self.sender_id
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"SMS sent via Custom API to {phone_number}")
                return True, "SMS sent successfully"
            else:
                logger.error(f"Custom API error: {response.status_code}")
                return False, f"HTTP Error: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Custom API error: {str(e)}")
            return False, f"Failed to send SMS: {str(e)}"
    
    def _send_via_console(self, phone_number, message):
        """Console mode for development (prints to console)"""
        print("\n" + "="*60)
        print("📱 SMS NOTIFICATION (Console Mode)")
        print("="*60)
        print(f"To: {phone_number}")
        print(f"From: {self.sender_id}")
        print(f"Message:\n{message}")
        print("="*60 + "\n")
        
        logger.info(f"SMS (console mode) to {phone_number}: {message}")
        return True, "SMS sent (console mode)"


# SMS Templates
class SMSTemplates:
    """Pre-defined SMS templates"""
    
    @staticmethod
    def admission_confirmation(student_name, roll_number, class_name):
        return f"Dear {student_name}, Welcome to our school! Your admission is confirmed. Roll No: {roll_number}, Class: {class_name}. Best wishes!"
    
    @staticmethod
    def result_published(student_name, exam_name, cgpa, grade):
        return f"Dear Parent, {exam_name} results are published. {student_name} scored CGPA: {cgpa}, Grade: {grade}. Check portal for details."
    
    @staticmethod
    def fee_reminder(student_name, amount, due_date):
        return f"Fee Reminder: {student_name}'s fee of BDT {amount} is due on {due_date}. Please pay at your earliest convenience."
    
    @staticmethod
    def attendance_alert(student_name, date, status):
        return f"Attendance Alert: {student_name} was marked {status} on {date}. Please contact school if this is incorrect."
    
    @staticmethod
    def exam_schedule(student_name, exam_name, date, time):
        return f"Exam Notice: {exam_name} for {student_name} is scheduled on {date} at {time}. Please be on time."
    
    @staticmethod
    def meeting_invitation(parent_name, date, time, purpose):
        return f"Dear {parent_name}, You are invited for a meeting on {date} at {time}. Purpose: {purpose}. Please confirm attendance."
    
    @staticmethod
    def custom_message(message):
        return message


# Convenience function
def send_sms(phone_number, message):
    """Quick function to send SMS"""
    service = SMSService()
    return service.send_sms(phone_number, message)


# Bulk SMS function
def send_bulk_sms(phone_numbers, message):
    """Send SMS to multiple recipients"""
    service = SMSService()
    results = []
    
    for phone in phone_numbers:
        success, msg = service.send_sms(phone, message)
        results.append({
            'phone': phone,
            'success': success,
            'message': msg
        })
    
    return results
