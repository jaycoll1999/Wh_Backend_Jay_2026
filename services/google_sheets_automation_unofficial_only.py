#!/usr/bin/env python3
"""
🔥 GOOGLE SHEETS AUTOMATION SERVICE - UNOFFICIAL WHATSAPP API ONLY

This service handles Google Sheet triggers using ONLY Unofficial WhatsApp API.
Completely removes all official WhatsApp logic and uses device-based messaging only.

✅ FEATURES:
- Process triggers using Unofficial WhatsApp devices only
- Send messages via WhatsApp Engine (unofficial)
- Device validation and health checks
- Proper error handling and logging

❌ REMOVED:
- All official WhatsApp API logic
- OfficialWhatsAppConfig dependencies
- OfficialMessageService dependencies
- Template-based messaging logic
"""

import asyncio
import logging
import uuid
import re
from datetime import datetime, timedelta, timezone, time, date
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, text

from models.google_sheet import GoogleSheet, GoogleSheetTrigger, GoogleSheetTriggerHistory, SheetStatus, TriggerType, TriggerHistoryStatus
from models.device import Device
from services.google_sheets_service import GoogleSheetsService
from services.unified_service import UnifiedWhatsAppService
from schemas.unified import UnifiedMessageRequest, MessageType
from services.device_validator import validate_device_before_send

# 🔥 STATUS NORMALIZATION CONSTANTS
VALID_TRIGGER_STATUSES = {
    "scheduled": "SCHEDULED",
    "send": "SEND", 
    "sent": "SENT",
    "sending": "SENDING",
    "failed": "FAILED"
}

logger = logging.getLogger(__name__)

class GoogleSheetsAutomationServiceUnofficial:
    """
    🔥 UNOFFICIAL WHATSAPP GOOGLE SHEETS AUTOMATION
    
    Processes Google Sheet triggers using ONLY Unofficial WhatsApp API
    """
    
    # 🔥 IN-MEMORY ROW LOCKING
    # Tracks (sheet_id, row_number) combinations currently being processed
    _processing_rows = set()
    
    def __init__(self, db: Session):
        self.db = db
        self.sheets_service = GoogleSheetsService()
        self.unified_service = UnifiedWhatsAppService(db)

    def get_case_insensitive_value(self, data: Dict[str, Any], key: Optional[str]) -> Any:
        """Helper to get value from dictionary with case-insensitive and stripped key matching"""
        if not key:
            return None
        
        # Normalize target key
        key_clean = key.strip().lower()
        
        # Try direct match
        if key in data:
            return data[key]
        
        # Try case-insensitive and stripped match
        for k, v in data.items():
            if k.strip().lower() == key_clean:
                return v
        
        return None
    
    def format_phone_number(self, phone_number: str) -> str:
        """
        Format phone number - removes all non-digit characters.
        Does NOT prepends any country code by default to avoid hardcoding.
        If the number starts with 0 and is 11 digits, it's treated as a local number and the 0 is removed.
        """
        if not phone_number:
            return ""
        
        # Convert to string and strip
        val = str(phone_number).strip()
        
        # Remove all non-digit characters
        clean = re.sub(r'\D', '', val)
        
        if not clean:
            return ""

        # Valid WhatsApp numbers are usually 8-16 digits globally
        if len(clean) < 8 or len(clean) > 16:
            return ""
            
        return clean
    
    async def process_all_active_triggers(self):
        """Process all active triggers for all sheets - LEGACY METHOD FOR BACKWARD COMPATIBILITY"""
        logger.warning("⚠️  LEGACY METHOD CALLED: process_all_active_triggers() - This should only be called via on-demand API")
        try:
            # Check if google_sheets table exists
            try:
                self.db.execute(text("SELECT 1 FROM google_sheets LIMIT 1"))
            except Exception as table_error:
                logger.info(f"Google Sheets tables not found - skipping trigger processing: {str(table_error)}")
                return
            
            # Get all active sheets
            active_sheets = self.db.query(GoogleSheet).filter(
                GoogleSheet.status == SheetStatus.ACTIVE
            ).all()
            
            if not active_sheets:
                logger.info("No active Google Sheets found for trigger processing")
                return
            
            logger.info(f"🚀 Processing triggers for {len(active_sheets)} active sheets")
            
            for sheet in active_sheets:
                try:
                    # 🔥 SYNC-IN-ASYNC FIX: Wrap blocking Google Sheets data fetch in thread
                    rows_data, headers_data = await asyncio.to_thread(
                        self.sheets_service.get_sheet_data_with_headers,
                        spreadsheet_id=sheet.spreadsheet_id,
                        worksheet_name=sheet.worksheet_name or "Sheet1"
                    )
                    
                    await self.process_sheet_triggers(sheet, rows_data, headers_data)
                    
                except Exception as sheet_error:
                    logger.error(f"Error processing sheet {sheet.id}: {sheet_error}")
                    # Release DB session if it's stuck
                    if hasattr(self.db, 'rollback'):
                         self.db.rollback()
                    continue
            
            logger.info("✅ Completed processing all active sheets")
            
        except Exception as e:
            logger.error(f"❌ Error in process_all_active_triggers: {e}")
    
    async def process_sheet_triggers(self, sheet: GoogleSheet, rows_data: List[Dict[str, Any]], headers_data: List[str]):
        """
        Process all triggers for a specific sheet using unofficial WhatsApp API only
        """
        try:
            logger.info(f"📋 Processing triggers for sheet {sheet.sheet_name} ({sheet.id})")
            logger.info(f"   Sheet has {len(rows_data)} rows and {len(headers_data)} columns")
            
            # Get all enabled triggers for this sheet
            triggers = self.db.query(GoogleSheetTrigger).filter(
                and_(
                    GoogleSheetTrigger.sheet_id == sheet.id,
                    GoogleSheetTrigger.is_enabled == True
                )
            ).all()
            
            if not triggers:
                logger.info(f"   No enabled triggers found for sheet {sheet.sheet_name}")
                return
            
            logger.info(f"   Found {len(triggers)} enabled triggers")
            
            # Process each trigger
            for trigger in triggers:
                try:
                    await self.process_single_trigger(sheet, trigger, rows_data, headers_data)
                except Exception as trigger_error:
                    logger.error(f"   ❌ Error processing trigger {trigger.trigger_id}: {trigger_error}")
                    continue
            
            logger.info(f"✅ Completed processing triggers for sheet {sheet.sheet_name}")
            
        except Exception as e:
            logger.error(f"❌ Error processing sheet triggers: {e}")
    
    async def process_single_trigger(self, sheet: GoogleSheet, trigger: GoogleSheetTrigger, 
                                  rows_data: List[Dict[str, Any]], headers_data: List[str]):
        """
        Process a single trigger using unofficial WhatsApp API only
        """
        try:
            # Determine which device to use: trigger-specific or sheet-default
            # Validate device exists and is connected (OR Round Robin is configured)
            device_id = trigger.device_id or (sheet.device_id if sheet else None)
            multi_devices = (trigger.trigger_config or {}).get('multi_device_ids', [])
            
            if not device_id and not multi_devices:
                logger.error(f"   ❌ Trigger {trigger.trigger_id} has no device_id assigned (and no multi-device Round Robin) - skipping")
                return
            
            # Use one of the multi-devices as the 'active_device_id' if primary is missing
            # (Note: process_row_for_trigger handles the actual rotation)
            if not device_id and multi_devices:
                device_id = multi_devices[0]
                logger.info(f"   ℹ️ Primary device missing. Using first Round Robin device for validation: {device_id}")
            
            # Only proceed if we have rows data to check
            if not rows_data:
                # logger.info(f"   ℹ️ Trigger {trigger.trigger_id}: No data in sheet. Skipping.")
                return
                
            # 🔥 OPTIMIZATION: Check for rows first to avoid slamming the Engine health check every 10 seconds
            # We only need to check the device if we have something that MIGHT send.
            # (Note: In trigger mode, we iterate rows below)
            
            # Identify message owner (fallback to trigger.user_id if no sheet)
            triggered_by_user_id = trigger.user_id or (sheet.user_id if sheet else None)
            
            if not triggered_by_user_id:
                logger.error(f"   ❌ Trigger {trigger.trigger_id} has no user_id or sheet associated - skipping")
                return

            # For better visibility, let's log the trigger start
            logger.info(f"🎯 [AUTOMATION] Processing Trigger: {trigger.trigger_id} ({trigger.trigger_type}) for user {triggered_by_user_id}")
            
            # 🔥 GLOBAL SCHEDULING CHECK (IST Aware)
            if trigger.trigger_type == "time" and trigger.scheduled_at:
                # 1. The database stores '13:38:00+00:00' because of Pydantic default
                # 2. We interpret this literal '13:38' as Indian Standard Time (IST)
                ist_tz = timezone(timedelta(hours=5, minutes=30))
                literal_time = trigger.scheduled_at.replace(tzinfo=None)
                
                # Convert the literal IST time to a real UTC timestamp for accurate comparison
                sched_time_utc = literal_time.replace(tzinfo=ist_tz).astimezone(timezone.utc)
                
                now_utc = datetime.now(timezone.utc)
                
                # Check if it's too early
                if now_utc < sched_time_utc:
                    # Clearer logging for debugging
                    diff = sched_time_utc - now_utc
                    minutes_left = int(diff.total_seconds() / 60)
                    if minutes_left < 60:
                        logger.info(f"   ⏳ [IST/UTC] Trigger {trigger.trigger_id} waiting: {minutes_left} minutes until {literal_time.strftime('%H:%M')} IST")
                    return
                else:
                    logger.info(f"   🚀 Global schedule reached for {trigger.trigger_id} ({literal_time.strftime('%H:%M')} IST)!")
            
            # Get Device ID - Handle fallback logic once per poll if rows exist
            active_device_id = device_id
            
            logger.info(f"🔍 [AUTOMATION] Validating device {active_device_id}...")
            device_validation = validate_device_before_send(self.db, active_device_id, user_id=triggered_by_user_id)
            
            if not device_validation["valid"]:
                logger.warning(f"   ⚠️ Primary device {active_device_id} issues: {device_validation.get('error')}. Checking Fallback...")
                fallback_candidates = self.db.query(Device).filter(
                    Device.busi_user_id == triggered_by_user_id
                ).all()
                fallback_device_id = None
                
                for candidate in fallback_candidates:
                    # Validate candidate against truth (engine) and auto-heal local db status
                    candidate_valid = validate_device_before_send(self.db, candidate.device_id, user_id=triggered_by_user_id)
                    if candidate_valid["valid"]:
                        fallback_device_id = candidate.device_id
                        break

                if fallback_device_id:
                    logger.info(f"   ✅ Using fallback: {fallback_device_id}")
                    active_device_id = fallback_device_id
                else:
                    logger.error(f"   ❌ No connected devices found for user {sheet.user_id}. Cannot process triggers.")
                    return

            processed_count = 0
            match_count = 0
            logger.info(f"📊 [AUTOMATION] Scanning {len(rows_data)} rows for trigger conditions...")
            
            for row in rows_data:
                try:
                    # Process row and get result (Dict[str, Any])
                    res = await self.process_row_for_trigger(sheet, trigger, row, active_device_id, headers=headers_data)
                    
                    # Log and track result if it's a dictionary
                    if isinstance(res, dict):
                        if res.get("match"):
                            match_count += 1
                        if res.get("processed"):
                            processed_count += 1
                    else:
                        logger.warning(f"   ⚠️ Row {row.get('row_number')} returned unexpected result type: {type(res)}")
                except Exception as e:
                    logger.error(f"   ❌ Row {row.get('row_number')} error: {e}")
            
            # Update last processed row / last trigger time
            if trigger.trigger_type == "new_row" and rows_data:
                max_row = max(row.get('row_number', 0) for row in rows_data)
                trigger.last_processed_row = max(trigger.last_processed_row, max_row)
            
            trigger.last_triggered_at = datetime.now(timezone.utc)
            self.db.commit()
            
            logger.info(f"✅ [AUTOMATION] Trigger {trigger.trigger_id} complete: {match_count} matches, {processed_count} successfully processed.")
            
        except Exception as e:
            logger.error(f"   ❌ [AUTOMATION] Trigger {trigger.trigger_id} failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def process_row_for_trigger(self, sheet: GoogleSheet, trigger: GoogleSheetTrigger, row_info: Dict[str, Any], device_id: Any = None, headers: Optional[List[str]] = None):
        """
        Process a single row for trigger using unofficial WhatsApp API only
        """
        try:
            # Fallback to trigger.device_id if not passed
            device_id = device_id or trigger.device_id
            
            row_data = row_info['data']
            row_number = row_info['row_number']
            
            # 🔥 NEW: Skip Empty Rows (Filter out filler rows at the bottom of sheets)
            phone_val = self.get_case_insensitive_value(row_data, trigger.phone_column or 'Phone')
            if not phone_val or str(phone_val).strip() == "":
                # Don't log as warning, just debug-level skip to keep logs clean
                logger.debug(f"   Row {row_number}: Skipped (No phone number found)")
                return {"processed": False, "reason": "empty_row"}

            # 🔥 NEW: Early Local History Check (Crucial for Public Mode)
            # If we've already handled this row locally, skip it immediately without scanning again.
            try:
                # Search for any record for this trigger + row
                history_exists = self.db.query(GoogleSheetTriggerHistory).filter(
                    GoogleSheetTriggerHistory.trigger_id == str(trigger.trigger_id)
                ).all()
                
                already_handled_locally = False
                for h in history_exists:
                    if h.row_data and h.row_data.get('row_number') == row_number:
                        # 🔥 IMPROVEMENT: Only skip if it was successfully SENT
                        # If it previously FAILED or EXPIRED, allow retry if time is updated
                        if h.status == "sent":
                            already_handled_locally = True
                            break
                
                
                if already_handled_locally:
                    # Log the skip clearly so the user knows WHY nothing is happening
                    logger.info(f"   Row {row_number}: Already handled in DASHBOARD HISTORY. (Skip)")
                    return {"processed": False, "reason": "already_handled_locally"}
            except Exception as hist_err:
                logger.warning(f"   ⚠️ Row {row_number}: Local history check error: {hist_err}")

            # Skip if already processed (Only for new_row triggers)
            if trigger.trigger_type == "new_row" and row_number <= trigger.last_processed_row:
                logger.debug(f"   Row {row_number}: Skipped (Already processed: {trigger.last_processed_row})")
                return {"processed": False, "reason": "already_processed"}
            
            logger.info(f"   Row {row_number}: Inspecting row data: {row_data}")
            
            # 🔥 CRITICAL: Common status check for both time and status triggers
            status_column = trigger.status_column or 'Status'
            raw_status = self.get_case_insensitive_value(row_data, status_column)
            normalized_status = str(raw_status or "").strip().lower()
            
            # 1. Skip if already marked as finished in the sheet
            ALREADY_HANDLED = ['sent', 'send', 'processing', 'success', 'delivered', 'done', 'failed', 'expired']
            if normalized_status in ALREADY_HANDLED:
                # No need to log this every time for every column
                return {"processed": False, "reason": "already_handled"}
            
            # 2. Check in-memory lock (prevent concurrency issues)
            row_lock_key = f"{sheet.id}_{row_number}"
            if row_lock_key in self._processing_rows:
                logger.warning(f"   Row {row_number}: Skipped (Already being processed in this cycle)")
                return {"processed": False, "reason": "already_processing_memory"}

            # Mark as processing in memory
            self._processing_rows.add(row_lock_key)
            
            try:
                logger.debug(f"   Row {row_number}: Current status is '{normalized_status}' - proceeding with trigger check")

                # Handle trigger-specific conditions
                if trigger.trigger_type == "time":
                    # If we have a global scheduled_at, we already checked it in process_single_trigger
                    # So we just proceed to send this row if it doesn't have its own per-row Send_time column
                    if trigger.scheduled_at:
                        logger.info(f"   🎯 Row {row_number}: Processing via Global Schedule")
                        # 🔥 IST Aware Interpretation:
                        # Stored as '15:13+00:00', but we treat '15:13' as IST and convert to real UTC.
                        ist_tz = timezone(timedelta(hours=5, minutes=30))
                        literal_time = trigger.scheduled_at.replace(tzinfo=None)
                        send_time_value = literal_time.replace(tzinfo=ist_tz).astimezone(timezone.utc)
                    else:
                        # Fallback to old per-row column logic if global schedule is not set
                        send_time_value = self.get_case_insensitive_value(row_data, trigger.send_time_column)
                        
                        if not send_time_value:
                            logger.warning(f"   Row {row_number}: No send_time value in column '{trigger.send_time_column}'.")
                            return {"processed": False, "reason": "no_send_time"}
                    
                    # Parse send_time and check if it's time to send
                    try:
                        # 🔥 TIMEBASE RELIABILITY FIX (UTC Comparisons)
                        now_utc = datetime.now(timezone.utc)
                        ist_tz = timezone(timedelta(hours=5, minutes=30))
                        today_ist = now_utc.astimezone(ist_tz).date()
                        
                        if isinstance(send_time_value, (int, float)):
                            # 🔥 GOOGLE SHEETS SERIAL DATE FIX: 
                            # Excel/Google Sheets dates are days since 1899-12-30
                            # 0.5 = 12:00 PM, 45376.5 = 2024-03-25 12:00 PM
                            try:
                                base_date = datetime(1899, 12, 30)
                                send_time_raw = base_date + timedelta(days=float(send_time_value))
                                
                                # If it's just a time (value < 1), attach today's IST date
                                if float(send_time_value) < 1:
                                    send_time = datetime.combine(today_ist, send_time_raw.time())
                                else:
                                    send_time = send_time_raw
                            except:
                                logger.error(f"   ❌ Row {row_number}: Could not convert numeric time '{send_time_value}'")
                        
                        elif isinstance(send_time_value, str):
                            s = send_time_value.strip().upper()
                            
                            # Fix common formatting issues
                            s = s.replace("  ", " ") # Remove double spaces
                            
                            formats = [
                                '%H:%M:%S', '%H:%M',           # 24-hour
                                '%I:%M:%S %p', '%I:%M %p',     # 12-hour with AM/PM
                                '%H:%M:%S %p', '%H:%M %p',     # Tolerant 24-hour + AM/PM
                                '%d-%m-%Y %H:%M:%S', '%d-%m-%Y %H:%M', # Indian/Common with date
                                '%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M', # Slab/Slash format
                                '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', # ISO with date (space separator)
                                '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M', # ISO with date ('T' separator)
                                '%Y-%m-%d %I:%M:%S %p', '%Y-%m-%d %I:%M %p', # ISO + AM/PM
                            ]
                            
                            for fmt in formats:
                                try:
                                    parsed = datetime.strptime(s, fmt)
                                    # If the format only contained time (year defaults to 1900), attach today's date
                                    if parsed.year == 1900:
                                        # Use IST today
                                        ist_tz = timezone(timedelta(hours=5, minutes=30))
                                        today_ist = datetime.now(timezone.utc).astimezone(ist_tz).date()
                                        send_time = datetime.combine(today_ist, parsed.time()).replace(tzinfo=ist_tz)
                                    else:
                                        # Assume date is in IST if no tz info
                                        ist_tz = timezone(timedelta(hours=5, minutes=30))
                                        send_time = parsed.replace(tzinfo=ist_tz)
                                    break
                                except ValueError:
                                    continue
                                    
                            if not send_time:
                                # Last resort: Try regex for weird formats like 17:38:00 PM
                                match = re.search(r'(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?\s*(AM|PM)?', s)
                                if match:
                                    h = int(match.group(1))
                                    m = int(match.group(2))
                                    s_val = int(match.group(3)) if match.group(3) else 0
                                    ampm = match.group(4)
                                    
                                    if ampm == 'PM' and h < 12: 
                                        h += 12
                                    elif ampm == 'AM' and h == 12: 
                                        h = 0
                                        
                                    send_time = datetime.combine(today_ist, time(h, m, s_val))
                        
                        elif isinstance(send_time_value, (time, datetime)):
                            send_time = datetime.combine(today_ist, send_time_value) if isinstance(send_time_value, time) else send_time_value
                        
                        if not send_time:
                            raise ValueError(f"Could not parse time format: '{send_time_value}'")
                        
                        # Normalize everything to aware UTC for final comparison
                        if send_time.tzinfo is None:
                            # Default to IST if unspecified (common for user-input times)
                            ist_tz = timezone(timedelta(hours=5, minutes=30))
                            send_time = send_time.replace(tzinfo=ist_tz)
                        
                        now_utc = datetime.now(timezone.utc)
                        send_time_utc = send_time.astimezone(timezone.utc)
                        
                        # Use literal IST for logging to be clear for the user
                        ist_tz = timezone(timedelta(hours=5, minutes=30))
                        sched_ist_str = send_time_utc.astimezone(ist_tz).strftime('%H:%M')
                        
                        logger.info(f"   Row {row_number}: Time Check -> Schedule: {sched_ist_str} IST, Current IST: {now_utc.astimezone(ist_tz).strftime('%H:%M')}")
                        
                        if now_utc < send_time_utc:
                            # logger.info(f"   Row {row_number}: Time {send_time_utc} not reached yet.")
                            return {"processed": False, "reason": "time_not_reached"}
                            
                        # 🔥 RELIABILITY FIX: Expand window to 24 hours for triggered rows
                        if now_utc > send_time_utc + timedelta(hours=24):
                            logger.warning(f"   Row {row_number}: Time {send_time_utc} has expired (>24h). Will not send.")
                            
                            await self.create_trigger_history(
                                sheet, trigger, row_number, "", "", TriggerHistoryStatus.FAILED, 
                                f"Time expired (>24h window). Missed window for {send_time_utc}",
                                device_id=device_id
                            )
                            # Update sheet status to Expired 
                            await self.update_sheet_status(sheet, row_number, trigger.status_column, 'Expired')
                            
                            return {"processed": True, "reason": "time_expired"}

                        logger.info(f"   Row {row_number}: ⏰ Time Trigger Match! {send_time_utc} <= {now_utc}")
                        
                    except Exception as e:
                        logger.error(f"   ❌ Row {row_number}: Time parse error: {e}")
                        await self.create_trigger_history(
                            sheet, trigger, row_number, "", "", TriggerHistoryStatus.FAILED, 
                            f"Invalid time format: {send_time_value}",
                            device_id=device_id
                        )
                        return {"processed": False, "reason": "invalid_time"}
                
                else:
                    # Status-based trigger
                    trigger_value = str(trigger.trigger_value or 'Send').strip().lower()
                    if normalized_status != trigger_value:
                        logger.info(f"   Row {row_number}: Status '{normalized_status}' != trigger '{trigger_value}'")
                        return {"processed": False, "reason": "status_mismatch"}
                    
                    logger.info(f"   🎯 Row {row_number}: Status matches trigger value")
                
                # Extract phone number
                phone_column = trigger.phone_column or 'phone'
                phone = self.get_case_insensitive_value(row_data, phone_column)
                
                if not phone:
                    logger.warning(f"   Row {row_number}: No phone number in column '{phone_column}'. Available: {list(row_data.keys())}")
                    await self.create_trigger_history(
                        sheet, trigger, row_number, "", "", TriggerHistoryStatus.FAILED, 
                        f"No phone number found in column {phone_column}",
                        device_id=device_id
                    )
                    return {"processed": False, "reason": "no_phone"}
                
                # Format phone number
                formatted_phone = self.format_phone_number(str(phone))
                
                # 🔥 NEW: ROUND ROBIN & RANDOM DELAY
                import random
                
                # 1. Handle Multi-Template Cycling
                # If trigger_config has multi_templates, pick current and cycle
                config = trigger.trigger_config or {}
                multi_templates = config.get('multi_templates', [])
                
                if multi_templates:
                    current_t_idx = config.get('current_template_idx', 0)
                    if current_t_idx >= len(multi_templates):
                        current_t_idx = 0
                    
                    # Use template with processing
                    raw_template = multi_templates[current_t_idx]
                    message = self.sheets_service.process_message_template(raw_template, row_data)
                    logger.info(f"   📝 [ROUND ROBIN] Using Template {current_t_idx + 1} of {len(multi_templates)}")
                else:
                    # Original logic: prioritize message column over single template
                    message = ""
                    if trigger.message_column:
                        message_val = self.get_case_insensitive_value(row_data, trigger.message_column)
                        if message_val is not None:
                            message = str(message_val).strip()
                            if message:
                                logger.info(f"   📝 Using message from column '{trigger.message_column}': '{message[:50]}...'")
                    
                    if not message and trigger.message_template:
                        message = self.sheets_service.process_message_template(trigger.message_template, row_data)
                        logger.info(f"   📝 Using message template: '{message[:50]}...'")

                # Check if this is a media-only case (empty template but has media)
                if message == "" and trigger.media_url:
                    logger.info(f"   📎 [MEDIA-ONLY] Sending media without caption")
                    # Keep message as empty string for media-only
                elif not message:
                    error_msg = "No message content available"
                    logger.error(f"   ❌ Row {row_number}: {error_msg}")
                    await self.create_trigger_history(sheet, trigger, row_number, formatted_phone, "", TriggerHistoryStatus.FAILED, error_msg, device_id=device_id)
                    return {"processed": False, "reason": "no_message"}

                # 2. Handle Multi-Device Rotation
                multi_devices = config.get('multi_device_ids', [])
                if multi_devices:
                    current_d_idx = config.get('current_device_idx', 0)
                    if current_d_idx >= len(multi_devices):
                        current_d_idx = 0
                    
                    device_id = multi_devices[current_d_idx]
                    logger.info(f"   🎯 [ROUND ROBIN] Using Device {current_d_idx + 1} of {len(multi_devices)}: {device_id}")
                
                # 3. Randomized Delay (15-30s) - Human-like delivery
                # We only delay if it's NOT the very first successful send of this whole cycle to keep it responsive,
                # but for safety let's just always apply if it's within a loop.
                # Actually, most users want it to happen BETWEEN sends.
                if hasattr(self, '_last_send_time'):
                    # Check if last send was very recent
                    time_since_last = (datetime.now() - self._last_send_time).total_seconds()
                    if time_since_last < 5: # If we are processing rapidly
                        delay = random.uniform(15, 30)
                        logger.info(f"   ⏳ [STAGGERED] Waiting {delay:.1f}s before sending next...")
                        await asyncio.sleep(delay)

                # 🔥 RACE CONDITION FIX: Fetch the LATEST status right before processing
                status_column = trigger.status_column or 'Status'
                try:
                    # Clear cache to get fresh data
                    cache_key = f"{sheet.spreadsheet_id}:{sheet.worksheet_name or 'Sheet1'}"
                    if cache_key in self.sheets_service._sheet_cache:
                        del self.sheets_service._sheet_cache[cache_key]
                    
                    fresh_rows, _ = await asyncio.to_thread(
                        self.sheets_service.get_sheet_data_with_headers,
                        sheet.spreadsheet_id,
                        sheet.worksheet_name
                    )
                    
                    matching_row = next((r for r in fresh_rows if r['row_number'] == row_number), None)
                    if matching_row:
                        latest_status = str(self.get_case_insensitive_value(matching_row['data'], status_column) or "").strip().lower()
                        if latest_status in ALREADY_HANDLED:
                            logger.info(f"   Row {row_number}: 🛑 SKIPPED - Status changed to '{latest_status}' by another process.")
                            return {"processed": False, "reason": "already_handled_race_win"}
                except Exception as e:
                    logger.warning(f"   ⚠️ Row {row_number}: Could not verify fresh status: {e}")

                # Step 1: Update sheet status to "Processing"
                # 🔥 SAFETY: If we can't update to "Processing", we check internal history as a fallback
                status_updated = await self.update_sheet_status(sheet, row_number, status_column, "Processing", headers)
                
                if not status_updated:
                    # In Public Mode, we already did the history check at the very beginning of process_row_for_trigger.
                    # If we reached here, it means it's definitely a new row that needs sending.
                    if not getattr(self.sheets_service, 'has_real_credentials', False):
                        logger.info(f"   ✨ Row {row_number}: Public Bypass Mode active. Proceeding with send...")
                    else:
                        logger.warning(f"   ⚠️ Row {row_number}: Skipping send because sheet status could not be updated to 'Processing'")
                        return {"processed": False, "reason": "status_update_failed"}
                
                # Step 2: Send WhatsApp message via unified service (to handle credits)
                try:
                    logger.info(f"   📤 Sending WhatsApp message for row {row_number} (Credit Aware)")
                    logger.info(f"   Phone: {formatted_phone}")
                    logger.info(f"   Device: {device_id}")
                    logger.info(f"   User ID: {sheet.user_id}")
                    
                    # Create unified message request with media support
                    message_type = MessageType.TEXT
                    media_url = None
                    
                    # Check if trigger has media attached
                    logger.info(f"   Checking media - trigger.media_url: {trigger.media_url}, trigger.media_type: {trigger.media_type}")
                    if trigger.media_url and trigger.media_type:
                        # Normalize media type to match MessageType enum
                        media_type_lower = trigger.media_type.lower().strip()
                        if media_type_lower in ['image', 'images', 'jpg', 'jpeg', 'png', 'gif']:
                            message_type = MessageType.IMAGE
                        elif media_type_lower in ['video', 'videos', 'mp4', 'avi', 'mov']:
                            message_type = MessageType.VIDEO
                        elif media_type_lower in ['audio', 'audio', 'mp3', 'wav', 'ogg']:
                            message_type = MessageType.AUDIO
                        else:
                            message_type = MessageType.DOCUMENT
                        
                        # Convert HTTP URL back to local path for engine service
                        media_url = trigger.media_url
                        if media_url.startswith('http://localhost:8000/uploads/'):
                            media_url = media_url.replace('http://localhost:8000/uploads/', 'uploads/')
                        elif media_url.startswith('http://127.0.0.1:8000/uploads/'):
                            media_url = media_url.replace('http://127.0.0.1:8000/uploads/', 'uploads/')
                            
                        logger.info(f"   Including media: {message_type.value} from {trigger.media_url} -> {media_url}")
                    else:
                        message_type = MessageType.TEXT
                        media_url = None
                        logger.info(f"   No media attached - sending text only")
                    
                    msg_request = UnifiedMessageRequest(
                        to=formatted_phone,
                        type=message_type,
                        message=message,
                        media_url=media_url,
                        device_id=str(device_id),
                        user_id=str(sheet.user_id)
                    )
                    
                    logger.info(f"   Created message request - type: {message_type}, media_url: {media_url}")
                    
                    # Send via unified service which handles credits and balance checks
                    # 🔥 SYNC-IN-ASYNC FIX: Wrap blocking call in thread
                    send_response = await asyncio.to_thread(
                        self.unified_service.send_unified_message, 
                        msg_request
                    )
                    
                    if send_response.success:
                        # Step 3: Update sheet status to "Sent"
                        await self.update_sheet_status(sheet, row_number, status_column, "Sent", headers)
                        # 🔥 CRITICAL: Update local data so other triggers in same loop skip this
                        row_data[status_column] = "Sent"
                        
                        # Step 4: Save trigger history
                        await self.create_trigger_history(
                            sheet, trigger, row_number, formatted_phone, message, 
                            TriggerHistoryStatus.SENT, message_id=send_response.message_id,
                            device_id=device_id
                        )
                        
                        logger.info(f"   ✅ Row {row_number}: Message sent successfully via Unified Service")
                        
                        # 🔥 AFTER SUCCESSFUL SEND: Update Round Robin Indices & Track Last Send
                        self._last_send_time = datetime.now()
                        
                        config = trigger.trigger_config or {}
                        multi_templates = config.get('multi_templates', [])
                        multi_devices = config.get('multi_device_ids', [])
                        
                        if multi_templates or multi_devices:
                            if multi_templates:
                                config['current_template_idx'] = (config.get('current_template_idx', 0) + 1) % len(multi_templates)
                            if multi_devices:
                                config['current_device_idx'] = (config.get('current_device_idx', 0) + 1) % len(multi_devices)
                            
                            trigger.trigger_config = config
                            # SQLAlchemy session should auto-track this change in trigger_config JSON
                        
                        return {"processed": True, "status": "sent", "match": True}
                        
                    else:
                        raise Exception("Unified service reported failure without exception")
                        
                except Exception as e:
                    # Step 3: Update sheet status to "Failed"
                    # Log the specific error (could be insufficient credits)
                    error_msg = str(e).replace("WhatsApp Engine error: ", "")
                    await self.update_sheet_status(sheet, row_number, status_column, "Failed", headers)
                    row_data[status_column] = "Failed"
                    
                    # Step 4: Save trigger history
                    await self.create_trigger_history(
                        sheet, trigger, row_number, formatted_phone, message, 
                        TriggerHistoryStatus.FAILED, error_message=error_msg,
                        device_id=device_id
                    )
                    
                    logger.error(f"   ❌ Row {row_number}: Send failed - {error_msg}")
                    return {"processed": True, "status": "failed"}
                    
            except Exception as inner_e:
                logger.error(f"   ❌ Row {row_number}: Internal processing error - {inner_e}")
                return {"processed": False, "reason": "internal_error", "error": str(inner_e)}
            finally:
                # 🔓 RELEASE LOCK
                if row_lock_key in self._processing_rows:
                    self._processing_rows.remove(row_lock_key)
                    
        except Exception as outer_e:
            logger.error(f"   ❌ Row {row_number}: Outer processing error - {outer_e}")
            return {"processed": False, "reason": "outer_error", "error": str(outer_e)}
    
    async def update_sheet_status(self, sheet: GoogleSheet, row_number: int, status_column: str, status: str, headers: Optional[List[str]] = None) -> bool:
        """
        Update Google Sheet row status using the sheets service
        Returns True if update succeeded, False otherwise
        """
        try:
            # 🔥 SILENT SKIP IN PUBLIC MODE: Provide a helpful hint
            if not getattr(self.sheets_service, 'has_real_credentials', False):
                 logger.info(f"   ℹ️ Row {row_number}: Status '{status}' saved to your DASHBOARD (Spreadsheet is READ-ONLY in Public Mode).")
                 return False

            # 🔥 FIX: Use worksheet_name (tab name) instead of sheet_name (descriptive name)
            target_worksheet = sheet.worksheet_name or "Sheet1"
            
            # 🔥 SYNC-IN-ASYNC FIX: Use to_thread for Google Sheets blocking call
            success = await asyncio.to_thread(
                self.sheets_service.update_cell,
                sheet.spreadsheet_id,
                target_worksheet,
                row_number,
                status_column,
                status,
                headers=headers
            )
            if success:
                logger.info(f"   📝 Updated row {row_number} status to '{status}' in column '{status_column}'")
                return True
            else:
                # Don't log error here as update_cell already logs it.
                return False
        except Exception as e:
            # Only log error if we have credentials
            if getattr(self.sheets_service, 'has_real_credentials', False):
                logger.error(f"   ❌ Error updating sheet status for row {row_number}: {e}")
            return False
    
    async def create_trigger_history(self, sheet: GoogleSheet, trigger: GoogleSheetTrigger, 
                                 row_number: int, phone: str, message: str, 
                                 status: TriggerHistoryStatus, message_id: Optional[str] = None, 
                                 error_message: Optional[str] = None, device_id: Any = None):
        """
        Save trigger history after every row
        """
        try:
            from datetime import datetime
            history = GoogleSheetTriggerHistory(
                sheet_id=sheet.id,
                trigger_id=str(trigger.trigger_id),  # ✅ Cast UUID to string
                device_id=str(device_id or trigger.device_id), # ✅ Cast to string
                phone_number=phone,
                message_content=message,
                status=status.value,
                error_message=error_message,
                triggered_at=datetime.now(timezone.utc),  # ✅ Consistent UTC/IST handling
                row_data={
                    "row_number": row_number,
                    "trigger_id": str(trigger.trigger_id),
                    "message_id": message_id
                }
            )
            
            # 🔥 SYNC-IN-ASYNC FIX: Wrap DB commits in thread
            def save_history():
                self.db.add(history)
                self.db.commit()
            
            await asyncio.to_thread(save_history)
            
            logger.debug(f"   📋 Saved trigger history for row {row_number}: {status.value}")
            
        except Exception as e:
            logger.error(f"   Failed to save trigger history: {e}")
            self.db.rollback()

# Create alias for backward compatibility
GoogleSheetsAutomationService = GoogleSheetsAutomationServiceUnofficial
