ENQUEUED_FROM_QUERY = 100, "Enqueued directly from query."
ENQUEUED_FROM_ADMIN = 110, "Enqueued from Admin."
GENERATING_PAGES = 200, "Generating pages."
GENERATING_PAGES_COMPLETE = 220, "Finished generating pages."
FINALIZING = 700, "Running post-page steps."
FINALIZING_LOCKED = 701, "Failed to get lock when running post-page steps."

POST_VALIDATION = 500, "Uploading post-export validation list."
FETCH_VALIDATION = 550, "Fetching post-export validation."
VALIDATION_COMPLETE_LOCKED = 551, "Failed to get lock to perform post-validation tasks."
REFUNDING_INVALID = 560, "Refunding user credits for invalid emails."
SPAWN_MX = 600, "Generated mx-domain task group."

ALERT_XPERWEB = 750, "Notified xperweb of export completion."

POPULATE_DATA = 400, "Populating page directly from search data."
PAGES_SPAWNED = 350, "Scheduling batch of pages to process."
FINALIZE_PAGE = 300, "Page finalizing."

COLDLIST_PENDING = 1000, "Set for upload as coldemail list."

DOWNLOAD = 900, "Export accessed."
DOWNLOAD_VALIDATION = 800, "Export accessed for validation."
