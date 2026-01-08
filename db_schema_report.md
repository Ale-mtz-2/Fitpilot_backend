# FitPilot - Reporte de esquema (schema app)

- Generado: 2025-09-27T23:57:19+00:00
- Tablas encontradas: 40

## accounts (filas: 2)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.accounts_id_seq'::regclass); auto
- person_id (BIGINT); NOT NULL
- username (VARCHAR(100)); NOT NULL
- password_hash (VARCHAR(255)); NOT NULL
- is_active (BOOLEAN); NOT NULL; default true
- created_at (TIMESTAMP); NOT NULL; default now()
- updated_at (TIMESTAMP)
**Llave primaria**
- accounts_pkey: id
**Indices**
- accounts_username_key (UNIQUE): username
**Relaciones (FK)**
- accounts_person_id_fkey: person_id -> app.people(id)
**Restricciones unicas**
- accounts_username_key: username

## asset_events (filas: 0)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.asset_events_id_seq'::regclass); auto
- asset_id (BIGINT); NOT NULL
- event_type (VARCHAR(20)); NOT NULL
- performed_at (TIMESTAMP); NOT NULL; default now()
- notes (TEXT)
- cost (NUMERIC(12, 2))
- created_by (BIGINT)
**Llave primaria**
- asset_events_pkey: id
**Relaciones (FK)**
- asset_events_asset_id_fkey: asset_id -> app.assets(id) (ON DELETE CASCADE)
- asset_events_created_by_fkey: created_by -> app.accounts(id)

## asset_models (filas: 1)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.asset_models_id_seq'::regclass); auto
- asset_type_id (BIGINT); NOT NULL
- brand (VARCHAR(80))
- model_name (VARCHAR(120))
- maintenance_interval_days (INTEGER)
- maintenance_interval_classes (INTEGER)
- notes (TEXT)
**Llave primaria**
- asset_models_pkey: id
**Relaciones (FK)**
- asset_models_asset_type_id_fkey: asset_type_id -> app.asset_types(id)

## asset_seat_assignments (filas: 0)
**Columnas**
- asset_id (BIGINT); NOT NULL
- seat_id (BIGINT); NOT NULL
- assigned_at (TIMESTAMP); NOT NULL; default now()
- unassigned_at (TIMESTAMP)
**Llave primaria**
- asset_seat_assignments_pkey: asset_id, assigned_at
**Indices**
- uq_asset_active_assignment (UNIQUE): asset_id
- uq_seat_active_asset (UNIQUE): seat_id
**Relaciones (FK)**
- asset_seat_assignments_asset_id_fkey: asset_id -> app.assets(id) (ON DELETE CASCADE)
- asset_seat_assignments_seat_id_fkey: seat_id -> app.seats(id) (ON DELETE CASCADE)

## asset_types (filas: 4)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.asset_types_id_seq'::regclass); auto
- code (VARCHAR(50)); NOT NULL
- name (VARCHAR(100)); NOT NULL
- description (TEXT)
**Llave primaria**
- asset_types_pkey: id
**Indices**
- asset_types_code_key (UNIQUE): code
**Restricciones unicas**
- asset_types_code_key: code

## assets (filas: 14)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.assets_id_seq'::regclass); auto
- asset_model_id (BIGINT); NOT NULL
- serial_number (VARCHAR(120))
- purchase_date (DATE)
- status (VARCHAR(20)); NOT NULL; default 'in_service'::character varying
- created_at (TIMESTAMP); NOT NULL; default now()
- updated_at (TIMESTAMP); NOT NULL; default now()
- retired_at (TIMESTAMP)
**Llave primaria**
- assets_pkey: id
**Indices**
- assets_serial_number_key (UNIQUE): serial_number
**Relaciones (FK)**
- assets_asset_model_id_fkey: asset_model_id -> app.asset_models(id)
**Restricciones unicas**
- assets_serial_number_key: serial_number

## chat_kv (filas: 16)
**Columnas**
- wa_id (VARCHAR(50)); NOT NULL
- k (VARCHAR(100)); NOT NULL
- v (TEXT)
- updated_at (TIMESTAMP); NOT NULL; default CURRENT_TIMESTAMP

## chat_memory (filas: 40)
**Columnas**
- turno_id (BIGINT); NOT NULL; auto
- wa_id (VARCHAR(50)); NOT NULL
- role (VARCHAR(20)); NOT NULL
- content (TEXT); NOT NULL
- created_at (TIMESTAMP); NOT NULL; default CURRENT_TIMESTAMP

## class_sessions (filas: 501)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.class_sessions_id_seq'::regclass); auto
- class_type_id (BIGINT); NOT NULL
- venue_id (BIGINT); NOT NULL
- template_id (BIGINT)
- instructor_id (BIGINT)
- name (VARCHAR(120))
- start_at (TIMESTAMP); NOT NULL
- end_at (TIMESTAMP); NOT NULL
- capacity (INTEGER); NOT NULL
- status (VARCHAR(20)); NOT NULL; default 'scheduled'::character varying
- created_at (TIMESTAMP); NOT NULL; default now()
- updated_at (TIMESTAMP); NOT NULL; default now()
**Llave primaria**
- class_sessions_pkey: id
**Indices**
- idx_sessions_time: start_at, venue_id
**Relaciones (FK)**
- class_sessions_class_type_id_fkey: class_type_id -> app.class_types(id)
- class_sessions_instructor_id_fkey: instructor_id -> app.people(id)
- class_sessions_template_id_fkey: template_id -> app.class_templates(id)
- class_sessions_venue_id_fkey: venue_id -> app.venues(id)

## class_templates (filas: 5)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.class_templates_id_seq'::regclass); auto
- class_type_id (BIGINT); NOT NULL
- venue_id (BIGINT); NOT NULL
- default_capacity (INTEGER)
- default_duration_min (INTEGER); NOT NULL
- weekday (INTEGER); NOT NULL
- start_time_local (TIME); NOT NULL
- instructor_id (BIGINT)
- name (VARCHAR(120))
- is_active (BOOLEAN); NOT NULL; default true
- created_at (TIMESTAMP); NOT NULL; default now()
- updated_at (TIMESTAMP); NOT NULL; default now()
**Llave primaria**
- class_templates_pkey: id
**Relaciones (FK)**
- class_templates_class_type_id_fkey: class_type_id -> app.class_types(id)
- class_templates_instructor_id_fkey: instructor_id -> app.people(id)
- class_templates_venue_id_fkey: venue_id -> app.venues(id)

## class_types (filas: 4)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.class_types_id_seq'::regclass); auto
- code (VARCHAR(50)); NOT NULL
- name (VARCHAR(120)); NOT NULL
- description (TEXT)
**Llave primaria**
- class_types_pkey: id
**Indices**
- class_types_code_key (UNIQUE): code
**Restricciones unicas**
- class_types_code_key: code

## communications_opt_in (filas: 91)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.communications_opt_in_id_seq'::regclass); auto
- person_id (BIGINT); NOT NULL
- channel (VARCHAR(20)); NOT NULL
- granted_at (TIMESTAMP)
- revoked_at (TIMESTAMP)
- source (VARCHAR(80))
- evidence (JSONB)
- created_at (TIMESTAMP); NOT NULL; default now()
- updated_at (TIMESTAMP); NOT NULL; default now()
**Llave primaria**
- communications_opt_in_pkey: id
**Indices**
- idx_optin_active: channel, granted_at
- idx_optin_person_channel: person_id, channel
**Relaciones (FK)**
- communications_opt_in_person_id_fkey: person_id -> app.people(id) (ON DELETE CASCADE)

## contacts (filas: 319)
**Columnas**
- id (BIGINT); NOT NULL; auto
- wa_id (VARCHAR(30)); NOT NULL
- phone_number (VARCHAR(20)); NOT NULL
- name (VARCHAR(100))
- profile_name (VARCHAR(100))
- created_at (TIMESTAMP); default CURRENT_TIMESTAMP
- updated_at (TIMESTAMP); default CURRENT_TIMESTAMP
- is_saved (SMALLINT); NOT NULL; default 0

## conversations (filas: 146)
**Columnas**
- id (BIGINT); NOT NULL; auto
- contact_id (BIGINT); NOT NULL
- status (VARCHAR(30)); NOT NULL; default 'active'::character varying
- expiration_timestamp (TIMESTAMP)
- created_at (TIMESTAMP); default CURRENT_TIMESTAMP
- updated_at (TIMESTAMP); default CURRENT_TIMESTAMP

## form_submissions (filas: 0)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.form_submissions_id_seq'::regclass); auto
- person_id (BIGINT); NOT NULL
- form_id (VARCHAR(80))
- form_name (VARCHAR(120))
- submitted_at (TIMESTAMP); NOT NULL; default now()
- landing_url (TEXT)
- referrer_url (TEXT)
- utm_source (VARCHAR(80))
- utm_medium (VARCHAR(80))
- utm_campaign (VARCHAR(120))
- utm_term (VARCHAR(120))
- utm_content (VARCHAR(120))
- gclid (VARCHAR(200))
- fbclid (VARCHAR(200))
- payload (JSONB)
- created_at (TIMESTAMP); NOT NULL; default now()
**Llave primaria**
- form_submissions_pkey: id
**Indices**
- idx_form_submissions_campaign: utm_campaign, submitted_at
- idx_form_submissions_person: person_id, submitted_at
**Relaciones (FK)**
- form_submissions_person_id_fkey: person_id -> app.people(id) (ON DELETE CASCADE)

## interactive_responses (filas: 0)
**Columnas**
- id (BIGINT); NOT NULL; auto
- message_id (BIGINT); NOT NULL
- interactive_type (VARCHAR(30)); NOT NULL
- title (VARCHAR(100))
- button_payload (VARCHAR(255))
- list_id (VARCHAR(100))
- section_id (VARCHAR(100))
- created_at (TIMESTAMP); default CURRENT_TIMESTAMP

## lead_attributions (filas: 0)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.lead_attributions_id_seq'::regclass); auto
- lead_id (BIGINT); NOT NULL
- campaign_id (BIGINT)
- utm_source (VARCHAR(80))
- utm_medium (VARCHAR(80))
- utm_campaign (VARCHAR(120))
- utm_term (VARCHAR(120))
- utm_content (VARCHAR(120))
- landing_url (TEXT)
- click_at (TIMESTAMP)
- referrer_url (TEXT)
- gclid (VARCHAR(200))
- fbclid (VARCHAR(200))
- created_at (TIMESTAMP); NOT NULL; default now()
**Llave primaria**
- lead_attributions_pkey: id
**Indices**
- idx_lead_attr_campaign: campaign_id
- idx_lead_attr_lead: lead_id
**Relaciones (FK)**
- lead_attributions_campaign_id_fkey: campaign_id -> app.marketing_campaigns(id)
- lead_attributions_lead_id_fkey: lead_id -> app.leads(id) (ON DELETE CASCADE)

## lead_events (filas: 120)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.lead_events_id_seq'::regclass); auto
- lead_id (BIGINT); NOT NULL
- event_type (VARCHAR(30)); NOT NULL
- event_at (TIMESTAMP); NOT NULL; default now()
- payload (JSONB)
- notes (TEXT)
- created_by (BIGINT)
- created_at (TIMESTAMP); NOT NULL; default now()
**Llave primaria**
- lead_events_pkey: id
**Indices**
- idx_lead_events_lead_at: lead_id, event_at
- idx_lead_events_type: event_type, event_at
**Relaciones (FK)**
- lead_events_created_by_fkey: created_by -> app.accounts(id)
- lead_events_lead_id_fkey: lead_id -> app.leads(id) (ON DELETE CASCADE)

## lead_sources (filas: 9)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.lead_sources_id_seq'::regclass); auto
- code (VARCHAR(40)); NOT NULL
- name (VARCHAR(100)); NOT NULL
- created_at (TIMESTAMP); NOT NULL; default now()
**Llave primaria**
- lead_sources_pkey: id
**Indices**
- lead_sources_code_key (UNIQUE): code
**Restricciones unicas**
- lead_sources_code_key: code

## leads (filas: 91)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.leads_id_seq2'::regclass); auto
- person_id (BIGINT); NOT NULL
- source_id (BIGINT); NOT NULL
- status (VARCHAR(20)); NOT NULL; default 'new'::character varying
- score (INTEGER)
- owner_account_id (BIGINT)
- notes (TEXT)
- created_at (TIMESTAMP); NOT NULL; default now()
- updated_at (TIMESTAMP); NOT NULL; default now()
- converted_at (TIMESTAMP)
- legacy_id (INTEGER)
- migrated_at (TIMESTAMP); default now()
**Llave primaria**
- leads_pkey: id
**Indices**
- idx_leads_person_status: person_id, status
- idx_leads_source_created: source_id, created_at
- idx_leads_status_updated: status, updated_at
- uq_lead_active_per_source (UNIQUE): person_id, source_id
**Relaciones (FK)**
- leads_owner_account_id_fkey: owner_account_id -> app.accounts(id)
- leads_person_id_fkey: person_id -> app.people(id) (ON DELETE CASCADE)
- leads_source_id_fkey: source_id -> app.lead_sources(id)

## marketing_campaigns (filas: 0)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.marketing_campaigns_id_seq'::regclass); auto
- platform (VARCHAR(30))
- name (VARCHAR(160)); NOT NULL
- channel (VARCHAR(30))
- external_id (VARCHAR(120))
- start_at (TIMESTAMP)
- end_at (TIMESTAMP)
- created_at (TIMESTAMP); NOT NULL; default now()
- updated_at (TIMESTAMP); NOT NULL; default now()
**Llave primaria**
- marketing_campaigns_pkey: id
**Indices**
- idx_campaigns_platform_dates: platform, start_at, end_at

## media (filas: 10)
**Columnas**
- id (BIGINT); NOT NULL; auto
- message_id (BIGINT); NOT NULL
- media_type (VARCHAR(30)); NOT NULL
- mime_type (VARCHAR(100))
- sha256 (VARCHAR(64))
- filename (VARCHAR(255))
- file_size (BIGINT)
- media_url (VARCHAR(255))
- caption (TEXT)
- created_at (TIMESTAMP); default CURRENT_TIMESTAMP
- downloaded (SMALLINT)
- download_time (TIMESTAMP)
- download_failed (SMALLINT); default 0

## membership_plans (filas: 5)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.membership_plans_id_seq'::regclass); auto
- name (VARCHAR(120)); NOT NULL
- description (TEXT)
- price (NUMERIC(12, 2)); NOT NULL
- duration_value (INTEGER); NOT NULL
- duration_unit (VARCHAR(10)); NOT NULL
- class_limit (INTEGER)
- fixed_time_slot (BOOLEAN); NOT NULL; default false
- max_sessions_per_day (INTEGER)
- max_sessions_per_week (INTEGER)
- created_at (TIMESTAMP); NOT NULL; default now()
- updated_at (TIMESTAMP)
**Llave primaria**
- membership_plans_pkey: id

## membership_subscriptions (filas: 2557)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.membership_subscriptions_id_seq'::regclass); auto
- person_id (BIGINT); NOT NULL
- plan_id (BIGINT); NOT NULL
- start_at (TIMESTAMP); NOT NULL
- end_at (TIMESTAMP); NOT NULL
- status (VARCHAR(20)); NOT NULL
- created_by (BIGINT)
- created_at (TIMESTAMP); NOT NULL; default now()
- updated_at (TIMESTAMP)
**Llave primaria**
- membership_subscriptions_pkey: id
**Indices**
- idx_subscriptions_person: person_id, status, end_at
**Relaciones (FK)**
- membership_subscriptions_created_by_fkey: created_by -> app.accounts(id)
- membership_subscriptions_person_id_fkey: person_id -> app.people(id)
- membership_subscriptions_plan_id_fkey: plan_id -> app.membership_plans(id)

## message_statuses (filas: 769)
**Columnas**
- id (BIGINT); NOT NULL; auto
- message_id (BIGINT); NOT NULL
- status (VARCHAR(30)); NOT NULL
- timestamp (TIMESTAMP); NOT NULL
- created_at (TIMESTAMP); default CURRENT_TIMESTAMP

## messages (filas: 1482)
**Columnas**
- id (BIGINT); NOT NULL; auto
- wa_message_id (VARCHAR(100))
- conversation_id (BIGINT); NOT NULL
- contact_id (BIGINT); NOT NULL
- direction (VARCHAR(30)); NOT NULL
- message_type (VARCHAR(30)); NOT NULL
- text_content (TEXT)
- template_id (BIGINT)
- context_message_id (VARCHAR(100))
- timestamp (TIMESTAMP); NOT NULL
- created_at (TIMESTAMP); default CURRENT_TIMESTAMP
- is_processed (SMALLINT); default 0
- processed_at (TIMESTAMP)
- is_temp (SMALLINT); default 0

## payments (filas: 2552)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.payments_id_seq'::regclass); auto
- subscription_id (BIGINT)
- person_id (BIGINT); NOT NULL
- amount (NUMERIC(12, 2)); NOT NULL
- paid_at (TIMESTAMP); NOT NULL; default now()
- method (VARCHAR(40)); NOT NULL
- provider (VARCHAR(40))
- provider_payment_id (VARCHAR(120))
- external_reference (VARCHAR(120))
- status (VARCHAR(20)); NOT NULL; default 'COMPLETED'::character varying
- comment (TEXT)
- recorded_by (BIGINT)
- created_at (TIMESTAMP); NOT NULL; default now()
**Llave primaria**
- payments_pkey: id
**Indices**
- idx_payments_person_paidat: person_id, paid_at
**Relaciones (FK)**
- payments_person_id_fkey: person_id -> app.people(id)
- payments_recorded_by_fkey: recorded_by -> app.accounts(id)
- payments_subscription_id_fkey: subscription_id -> app.membership_subscriptions(id)

## people (filas: 344)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.people_id_seq'::regclass); auto
- full_name (VARCHAR(200))
- phone_number (VARCHAR(32))
- email (VARCHAR(200))
- wa_id (VARCHAR(100))
- created_at (TIMESTAMP); NOT NULL; default now()
- updated_at (TIMESTAMP); NOT NULL; default now()
- deleted_at (TIMESTAMP)
**Llave primaria**
- people_pkey: id
**Indices**
- idx_people_email: email
- idx_people_phone: phone_number

## person_roles (filas: 366)
**Columnas**
- person_id (BIGINT); NOT NULL
- role_id (BIGINT); NOT NULL
- created_at (TIMESTAMP); NOT NULL; default now()
**Llave primaria**
- person_roles_pkey: person_id, role_id
**Relaciones (FK)**
- person_roles_person_id_fkey: person_id -> app.people(id)
- person_roles_role_id_fkey: role_id -> app.roles(id)

## reservations (filas: 598)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.reservations_id_seq'::regclass); auto
- session_id (BIGINT); NOT NULL
- person_id (BIGINT); NOT NULL
- seat_id (BIGINT)
- status (VARCHAR(20)); NOT NULL; default 'reserved'::character varying
- reserved_at (TIMESTAMP); NOT NULL; default now()
- checkin_at (TIMESTAMP)
- checkout_at (TIMESTAMP)
- waitlist_position (INTEGER)
- idempotency_key (VARCHAR(120))
- source (VARCHAR(20)); NOT NULL; default 'manual'::character varying
**Llave primaria**
- reservations_pkey: id
**Indices**
- idx_reservations_person: person_id, reserved_at
- reservations_session_id_person_id_key (UNIQUE): session_id, person_id
- uq_reservations_seat_once (UNIQUE): session_id, seat_id
**Relaciones (FK)**
- reservations_person_id_fkey: person_id -> app.people(id)
- reservations_seat_id_fkey: seat_id -> app.seats(id)
- reservations_session_id_fkey: session_id -> app.class_sessions(id) (ON DELETE CASCADE)
**Restricciones unicas**
- reservations_session_id_person_id_key: session_id, person_id

## roles (filas: 5)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.roles_id_seq'::regclass); auto
- code (VARCHAR(50)); NOT NULL
- description (VARCHAR(200))
- created_at (TIMESTAMP); NOT NULL; default now()
**Llave primaria**
- roles_pkey: id
**Indices**
- roles_code_key (UNIQUE): code
**Restricciones unicas**
- roles_code_key: code

## seat_types (filas: 4)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.seat_types_id_seq'::regclass); auto
- code (VARCHAR(50)); NOT NULL
- name (VARCHAR(100)); NOT NULL
- description (TEXT)
**Llave primaria**
- seat_types_pkey: id
**Indices**
- seat_types_code_key (UNIQUE): code
**Restricciones unicas**
- seat_types_code_key: code

## seats (filas: 14)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.seats_id_seq'::regclass); auto
- venue_id (BIGINT); NOT NULL
- label (VARCHAR(50)); NOT NULL
- row_number (INTEGER)
- col_number (INTEGER)
- is_active (BOOLEAN); NOT NULL; default true
- seat_type_id (BIGINT)
**Llave primaria**
- seats_pkey: id
**Indices**
- seats_venue_id_label_key (UNIQUE): venue_id, label
**Relaciones (FK)**
- seats_seat_type_id_fkey: seat_type_id -> app.seat_types(id)
- seats_venue_id_fkey: venue_id -> app.venues(id) (ON DELETE CASCADE)
**Restricciones unicas**
- seats_venue_id_label_key: venue_id, label

## sessions (filas: 117)
**Columnas**
- id (INTEGER); NOT NULL; auto
- refresh_token (VARCHAR(255)); NOT NULL
- session (VARCHAR(255)); NOT NULL
- device_name (VARCHAR(255))
- ip_address (INET)
- last_active_at (TIMESTAMP)
- revoked_at (TIMESTAMP)
- user_agent (VARCHAR(255))
- user_id (INTEGER); NOT NULL
- created_at (TIMESTAMP); default CURRENT_TIMESTAMP
- updated_at (TIMESTAMP)
- deleted_at (TIMESTAMP)
**Indices**
- idx_sessions_last_active: last_active_at

## standing_booking_exceptions (filas: 0)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.standing_booking_exceptions_id_seq'::regclass); auto
- standing_booking_id (BIGINT); NOT NULL
- session_date (DATE); NOT NULL
- action (VARCHAR(20)); NOT NULL
- new_session_id (BIGINT)
- notes (TEXT)
- created_at (TIMESTAMP); NOT NULL; default now()
**Llave primaria**
- standing_booking_exceptions_pkey: id
**Indices**
- standing_booking_exceptions_standing_booking_id_session_dat_key (UNIQUE): standing_booking_id, session_date
**Relaciones (FK)**
- standing_booking_exceptions_new_session_id_fkey: new_session_id -> app.class_sessions(id)
- standing_booking_exceptions_standing_booking_id_fkey: standing_booking_id -> app.standing_bookings(id) (ON DELETE CASCADE)
**Restricciones unicas**
- standing_booking_exceptions_standing_booking_id_session_dat_key: standing_booking_id, session_date

## standing_bookings (filas: 45)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.standing_bookings_id_seq'::regclass); auto
- person_id (BIGINT); NOT NULL
- subscription_id (BIGINT); NOT NULL
- template_id (BIGINT); NOT NULL
- seat_id (BIGINT)
- start_date (DATE); NOT NULL
- end_date (DATE); NOT NULL
- status (VARCHAR(20)); NOT NULL; default 'active'::character varying
- created_at (TIMESTAMP); NOT NULL; default now()
**Llave primaria**
- standing_bookings_pkey: id
**Relaciones (FK)**
- standing_bookings_person_id_fkey: person_id -> app.people(id)
- standing_bookings_seat_id_fkey: seat_id -> app.seats(id)
- standing_bookings_subscription_id_fkey: subscription_id -> app.membership_subscriptions(id) (ON DELETE CASCADE)
- standing_bookings_template_id_fkey: template_id -> app.class_templates(id)

## venues (filas: 1)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.venues_id_seq'::regclass); auto
- name (VARCHAR(120)); NOT NULL
- description (TEXT)
- capacity (INTEGER); NOT NULL
- address (VARCHAR(200))
- created_at (TIMESTAMP); NOT NULL; default now()
- updated_at (TIMESTAMP); NOT NULL; default now()
**Llave primaria**
- venues_pkey: id

## webhook_logs (filas: 190)
**Columnas**
- id (BIGINT); NOT NULL; auto
- event_type (VARCHAR(50)); NOT NULL
- x_request_id (VARCHAR(128))
- payload (JSON)
- processed (SMALLINT); default 1
- created_at (TIMESTAMP); default CURRENT_TIMESTAMP

## whatsapp_templates (filas: 7)
**Columnas**
- id (BIGINT); NOT NULL; auto
- template_name (VARCHAR(100)); NOT NULL
- template_namespace (VARCHAR(100)); NOT NULL
- template_language (VARCHAR(10)); NOT NULL
- template_status (VARCHAR(30)); NOT NULL
- components (JSON)
- created_at (TIMESTAMP); default CURRENT_TIMESTAMP
- updated_at (TIMESTAMP); default CURRENT_TIMESTAMP

## whatsapp_threads (filas: 91)
**Columnas**
- id (BIGINT); NOT NULL; default nextval('app.whatsapp_threads_id_seq'::regclass); auto
- person_id (BIGINT); NOT NULL
- wa_id (VARCHAR(100))
- phone_e164 (VARCHAR(32))
- last_inbound_at (TIMESTAMP)
- last_outbound_at (TIMESTAMP)
- last_message_snippet (TEXT)
- is_open (BOOLEAN); NOT NULL; default true
- provider (VARCHAR(40))
- created_at (TIMESTAMP); NOT NULL; default now()
- updated_at (TIMESTAMP); NOT NULL; default now()
**Llave primaria**
- whatsapp_threads_pkey: id
**Indices**
- idx_wa_threads_wa_id: wa_id
- uq_wa_thread_person (UNIQUE): person_id
**Relaciones (FK)**
- whatsapp_threads_person_id_fkey: person_id -> app.people(id) (ON DELETE CASCADE)
