```plantuml
@startuml c2-third-party-event-ingestion-hybrid
!include <C4/C4_Container>
!include <awslib14/AWSCommon>
!include <awslib14/ApplicationIntegration/SimpleQueueServiceQueue>
!include <awslib14/ApplicationIntegration/EventBridge>
!include <awslib14/Storage/SimpleStorageService>
!include <awslib14/Database/RDS>
!include <awslib14/Database/DynamoDB>
!include <tupadr3/devicons2/spring_original>
!include <tupadr3/font-awesome-5/clock>

SHOW_PERSON_OUTLINE()

AddRelTag("async", $textColor=$ARROW_FONT_COLOR, $lineColor=$ARROW_COLOR, $lineStyle=DashedLine())
AddRelTag("inline", $textColor=$ARROW_FONT_COLOR, $lineColor=$ARROW_COLOR, $lineStyle=DashedLine())
AddRelTag("claim", $textColor="#6b5b95", $lineColor="#6b5b95", $lineStyle=DottedLine())

LAYOUT_WITH_LEGEND()


title C2 Container Diagram: Third Party Activity Event Ingestion (EventBridge routing, hybrid inline + claim-check)

' -- Trigger and external providers -------------------------
Person(athlete, "Athlete", "Records a workout on a wearable")
System_Ext(providers, "Provider Cloud Platforms", "Garmin, Fitbit, Polar, Suunto, Coros, Amazfit. Hold recorded activity files and send webhooks", $sprite="clock")

' -- Event buses and shared stores --------------------------
ContainerQueue(eventbridge_in, "Activity Ingestion Event Bus", "AWS EventBridge", "One bus for all provider activity events. The detail is an ActivityProcessingMessage. Two rules split by detail-type: activity.inline carries fileData, activity.claimcheck carries an S3 reference", $sprite="EventBridge")
ContainerQueue(eventbridge_out, "ActivityCreated Event Bus", "AWS EventBridge", "Carries the ActivityCreatedEvent (source activity-service, detail-type ActivityCreatedEvent). Rules fan it out to the activityeventprocessor listener queues", $sprite="EventBridge")
Container(activity_files_bucket, "Activity Files Bucket", "AWS S3", "Claim-check store for files over 1MB. Holds the vendor file (FIT/TCX/GPX); the claim-check message carries only its S3 key and checksum", $sprite="SimpleStorageService")

' -- Integration platform (third-party-integrations repo) ---
System_Boundary(integration_platform, "Third-Party Integration Platform") {
    Container(integration_svc, "Provider Integration Services", "Java 25, Spring Boot 4, ECS", "Six microservices, one per provider. Receive webhooks, fetch activity files via OAuth REST, then send a small file inline or store a big file and send a claim-check ActivityProcessingMessage", $sprite="spring_original")
    ContainerQueue(webhook_queue, "Provider Webhook Queues", "AWS SQS FIFO", "Per provider buffer between webhook receipt and file fetch (garmin-webhook.fifo, polar-webhook.fifo, ...)", $sprite="SimpleQueueServiceQueue")
}

' -- Activity processing system (processing repo) -----------
System_Boundary(processing_system, "Activity Processing System") {
    ContainerQueue(processing_queue_inline, "Processing Queue (inline)", "AWS SQS FIFO", "Target for activity.inline events, ordered by userId. Body is an ActivityProcessingMessage with fileData populated, plus AdditionalData", $sprite="SimpleQueueServiceQueue")
    ContainerQueue(processing_queue_claim, "Processing Queue (claim-check)", "AWS SQS FIFO", "Target for activity.claimcheck events, ordered by userId. Body is an ActivityProcessingMessage with fileData replaced by an S3 reference plus checksum and AdditionalData, no bytes", $sprite="SimpleQueueServiceQueue")
    Container(processing_svc, "Activity Processing Service", "Java 25, Spring Boot 4, ECS", "One service, two SQS listeners. Takes the file inline or reads it from S3, parses it, de-duplicates, adds elevation and calories, saves the trip, publishes the ActivityCreatedEvent", $sprite="spring_original")
    ContainerDb(dynamo, "Idempotency Store", "AWS DynamoDB", "ActivityDuplicates, hash key idempotencyKey = provider|userId|activityId with a TTL. One ingestion per activity", $sprite="DynamoDB")
    ContainerDb(runkeeper_db, "Runkeeper DB", "PostgreSQL", "Trips, activities, users, tags", $sprite="RDS")
}

' -- Downstream consumer (activityeventprocessor) -----------
ContainerQueue(aep_queues, "Activity Event Queues", "AWS SQS", "One queue per listener. EventBridge rules target the queues whose listeners read ActivityCreatedEvent directly (iterable, personal_record, feed_base, user_stats, shoe_association, goals, adaptive_workout, achievement, challenge_completion, push_notification, amplitude). feed_goal, feed_pr and stats_alert are fed by plain SQS sends from other listeners, not by EventBridge", $sprite="SimpleQueueServiceQueue")
Container(monolith, "Activity Event Processor", "Stripes, Java, Tomcat", "A separate WAR on its own Tomcat, built from the Runkeeper monolith core. Each listener polls its own queue, unwraps the EventBridge envelope, and runs one side effect: user stats, feed items, personal records, goals, shoe association, achievements, challenges, push, Iterable email, Amplitude")

' -- Relationships ------------------------------------------
Rel(athlete, providers, "1. Records a workout")
Rel(providers, integration_svc, "2. Sends activity webhook", "HTTPS POST")
Rel(integration_svc, webhook_queue, "3. Buffers notification", "async, SQS", $tags="async")
Rel(webhook_queue, integration_svc, "4. Delivers notification", "SQS listener", $tags="async")
Rel(integration_svc, providers, "5. Fetches activity file", "OAuth2, HTTPS REST")

' Inline path (a): small file (raw under ~750 KB, event under 1 MB)
Rel(integration_svc, eventbridge_in, "6a. Publishes inline ActivityProcessingMessage (full fileData)", "async, JSON over EventBridge", $tags="inline")
Rel(eventbridge_in, processing_queue_inline, "7a. Rule: inline events", "EventBridge rule to SQS", $tags="inline")
Rel(processing_queue_inline, processing_svc, "8a. Delivers inline ActivityProcessingMessage", "SQS listener", $tags="inline")

' Claim-check path (b): big file (over 1 MB)
Rel(integration_svc, activity_files_bucket, "6b. Stores file over 1MB (claim-check)", "S3 PutObject", $tags="claim")
Rel(integration_svc, eventbridge_in, "7b. Publishes claim-check ActivityProcessingMessage (S3 reference + checksum)", "async, JSON over EventBridge", $tags="claim")
Rel(eventbridge_in, processing_queue_claim, "8b. Rule: claim-check events", "EventBridge rule to SQS", $tags="claim")
Rel(processing_queue_claim, processing_svc, "9b. Delivers claim-check ActivityProcessingMessage", "SQS listener", $tags="claim")
Rel(processing_svc, activity_files_bucket, "10b. Reads file by reference (claim-check only)", "S3 GetObject", $tags="claim")

' Persistence
Rel(processing_svc, dynamo, "11. Checks idempotencyKey (GetItem now, PutItem after publish)", "AWS SDK")
Rel(processing_svc, runkeeper_db, "12. Persists activity", "JDBC, MyBatis")

' Downstream: ActivityCreated flows through its own EventBridge bus
Rel(processing_svc, eventbridge_out, "13. Publishes ActivityCreatedEvent", "async, JSON over EventBridge", $tags="async")
Rel(eventbridge_out, aep_queues, "14. Routes ActivityCreatedEvent to listener queues", "EventBridge rule to SQS", $tags="async")
Rel(aep_queues, monolith, "15. Delivers ActivityCreatedEvent (EventBridge envelope)", "SQS long-poll", $tags="async")

' -- Layout hints -------------------------------------------
Lay_R(processing_queue_inline, processing_queue_claim)
Lay_R(processing_queue_claim, activity_files_bucket)
Lay_D(processing_svc, eventbridge_out)
Lay_D(eventbridge_out, aep_queues)

SHOW_LEGEND()

left footer
= Runkeeper third-party activity ingestion, hybrid C2 container diagram [2026-07-09]
Providers push webhooks to the integration services, which fetch the activity file over OAuth
REST. Then the size decides the path. A small file (raw under about 750 KB, so the base64
event stays under the 1 MB bus limit) goes inline: fileData rides in the ActivityProcessingMessage
on an activity.inline event, and an EventBridge rule routes it to the inline processing queue. A
big file goes claim-check: the service stores it in S3 and publishes an activity.claimcheck event
whose ActivityProcessingMessage holds just the S3 reference and checksum, which a second rule
routes to the claim-check queue. Both queues feed the one Activity Processing Service, which reads
S3 only for claim-check messages, then dedups against DynamoDB, writes the trip to PostgreSQL, and
emits the ActivityCreatedEvent to the downstream bus. That reaches activityeventprocessor, a
separate WAR on its own Tomcat built from the monolith core. Status: the downstream half is
live today. The inbound hybrid split is the target design; today the integrations publish the
ActivityProcessingMessage straight to the processing FIFO with the SQS Extended Client, which
offloads big bodies to S3 transparently, so there is no inline vs claim-check routing yet.
endfooter
@enduml

```

