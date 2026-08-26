window.DEMO_DATA = {
  certification: {
    name: "SnowPro Core",
    code: "COF-C03",
    questions: 1200,
    mockQuestions: 100,
    tasks: 19,
    domains: [
      { id: "architecture", number: 1, name: "Snowflake AI Data Cloud Features & Architecture", short: "Architecture", weight: 31, questionCount: 372, readiness: 78,
        tasks: [
          { id: "1.1", title: "Core architecture and platform concepts", lessons: ["Three-layer architecture", "Virtual warehouses", "Cloud services", "Micro-partitions"] },
          { id: "1.2", title: "Snowflake objects and hierarchy", lessons: ["Organizations and accounts", "Databases and schemas", "Tables and views", "Object ownership"] },
          { id: "1.3", title: "Storage capabilities", lessons: ["Time Travel", "Fail-safe", "Zero-copy cloning", "Retention behavior"] },
          { id: "1.4", title: "Compute and scaling", lessons: ["Warehouse sizing", "Multi-cluster warehouses", "Auto suspend / resume", "Concurrency"] },
          { id: "1.5", title: "Platform editions and services", lessons: ["Edition capabilities", "Serverless features", "Regions and clouds", "Feature availability"] },
          { id: "1.6", title: "Data architecture decisions", lessons: ["Structured vs semi-structured", "Native data types", "External data", "Design tradeoffs"] }
        ] },
      { id: "governance", number: 2, name: "Account Management & Data Governance", short: "Governance", weight: 20, questionCount: 240, readiness: 71,
        tasks: [
          { id: "2.1", title: "Security and access control", lessons: ["RBAC", "System roles", "Custom roles", "Privilege inheritance"] },
          { id: "2.2", title: "Governance and protection", lessons: ["Masking policies", "Row access policies", "Tags", "Classification"] },
          { id: "2.3", title: "Account administration", lessons: ["Users", "Authentication", "Network policies", "Resource monitors"] }
        ] },
      { id: "loading", number: 3, name: "Data Loading, Unloading & Connectivity", short: "Loading", weight: 18, questionCount: 216, readiness: 75,
        tasks: [
          { id: "3.1", title: "Bulk data loading", lessons: ["Stages", "File formats", "COPY INTO", "Load history"] },
          { id: "3.2", title: "Continuous ingestion and unloading", lessons: ["Snowpipe", "Streaming concepts", "COPY INTO location", "Unload patterns"] },
          { id: "3.3", title: "Connectivity and drivers", lessons: ["Connectors", "Drivers", "Partner tools", "Network connectivity"] }
        ] },
      { id: "performance", number: 4, name: "Performance Optimization, Querying & Transformation", short: "Performance", weight: 21, questionCount: 252, readiness: 62,
        tasks: [
          { id: "4.1", title: "Query execution and optimization", lessons: ["Query Profile", "Pruning", "Caching", "Join behavior"] },
          { id: "4.2", title: "Warehouse performance", lessons: ["Scale up vs scale out", "Queueing", "Concurrency", "Credit tradeoffs"] },
          { id: "4.3", title: "Data transformation", lessons: ["Streams", "Tasks", "Dynamic Tables", "ELT patterns"] },
          { id: "4.4", title: "Performance features", lessons: ["Clustering", "Search Optimization", "Materialized Views", "Optimization decisions"] }
        ] },
      { id: "collaboration", number: 5, name: "Data Collaboration", short: "Collaboration", weight: 10, questionCount: 120, readiness: 81,
        tasks: [
          { id: "5.1", title: "Secure data sharing", lessons: ["Shares", "Reader accounts", "Secure objects", "Provider / consumer"] },
          { id: "5.2", title: "Marketplace and listings", lessons: ["Listings", "Private exchange concepts", "Access patterns", "Governance"] },
          { id: "5.3", title: "Replication and collaboration architecture", lessons: ["Replication", "Failover concepts", "Cross-region", "Collaboration decisions"] }
        ] }
    ]
  },
  questions: [
    { id: "q1", domain: "architecture", task: "1.1", difficulty: "Applied", type: "Single select", stem: "A workload needs compute to scale independently from persisted table storage. Which Snowflake architecture characteristic directly enables this?", options: ["Micro-partition metadata is stored in virtual warehouses", "Compute and storage are separate services", "All queries use a single shared cluster", "Cloud services store table data locally"], answer: 1, explanation: "Snowflake separates compute from centralized storage. Virtual warehouses can be resized or multiplied without moving the persisted table data.", wrongWhy: "The distractors mix metadata, compute, and storage responsibilities. Virtual warehouses provide compute; they do not own persisted table storage." },
    { id: "q2", domain: "performance", task: "4.2", difficulty: "Exam", type: "Best answer", stem: "Users report query queueing during a predictable burst of many independent BI queries, while individual queries are already fast. What is the best first scaling action?", options: ["Increase table retention time", "Enable or expand multi-cluster warehouse capacity", "Add a clustering key to every queried table", "Disable result caching"], answer: 1, explanation: "When many independent queries are queuing, increasing concurrency with multi-cluster warehouse capacity is typically a better first action than scaling a single cluster up.", wrongWhy: "The issue described is concurrency, not scan efficiency or retention. Clustering can help pruning, but it does not directly add concurrent compute clusters." },
    { id: "q3", domain: "governance", task: "2.1", difficulty: "Applied", type: "Single select", stem: "A custom role must be able to query a table but should not gain ownership or unrelated administrative privileges. What is the most appropriate approach?", options: ["Grant OWNERSHIP on the database", "Grant the minimum required USAGE and SELECT privileges", "Grant ACCOUNTADMIN temporarily", "Transfer the table to the custom role"], answer: 1, explanation: "Snowflake RBAC supports least privilege. The role should receive the required container USAGE privileges and SELECT on the needed object, rather than ownership or broad administration.", wrongWhy: "Ownership and ACCOUNTADMIN exceed the stated requirement and expand the role's authority unnecessarily." },
    { id: "q4", domain: "loading", task: "3.1", difficulty: "Foundation", type: "Single select", stem: "Which command is commonly used to bulk load staged files into a Snowflake table?", options: ["COPY INTO <table>", "ALTER WAREHOUSE", "CREATE SHARE", "SHOW GRANTS"], answer: 0, explanation: "COPY INTO <table> loads files from internal or external stages into a target Snowflake table.", wrongWhy: "The other commands manage compute, collaboration, or metadata rather than loading staged files into a table." },
    { id: "q5", domain: "collaboration", task: "5.1", difficulty: "Applied", type: "Single select", stem: "A provider wants another Snowflake account to query governed data without copying the underlying data into a separate export file. Which capability best fits?", options: ["Secure Data Sharing", "Fail-safe", "Resource Monitor", "Search Optimization"], answer: 0, explanation: "Secure Data Sharing provides governed access to shared database objects without traditional file-based data copying between Snowflake accounts.", wrongWhy: "The other features address recovery, spend control, or query optimization—not provider-to-consumer data access." },
    { id: "q6", domain: "performance", task: "4.1", difficulty: "Exam", type: "Troubleshooting", stem: "A large table query scans far more micro-partitions than expected. Which diagnostic artifact should you inspect first to understand pruning and operator cost?", options: ["Query Profile", "Network Policy", "Account Usage login history", "Share metadata"], answer: 0, explanation: "Query Profile exposes operator-level execution details and scanning behavior, making it the first place to inspect for pruning and costly operators.", wrongWhy: "Security and sharing metadata do not explain scan behavior for an individual query plan." },
    { id: "q7", domain: "architecture", task: "1.3", difficulty: "Applied", type: "Best answer", stem: "A developer needs an isolated copy of a large production schema for testing without immediately duplicating all underlying storage. Which feature is designed for this?", options: ["Zero-copy cloning", "Resource monitors", "Reader accounts", "External functions"], answer: 0, explanation: "Zero-copy cloning creates metadata-based clones that initially share existing micro-partitions, avoiding an immediate full physical copy.", wrongWhy: "The alternatives address cost governance, external consumption, or external processing—not rapid storage-efficient environment copies." },
    { id: "q8", domain: "governance", task: "2.2", difficulty: "Exam", type: "Architecture decision", stem: "A column containing sensitive values should display differently depending on the querying role while keeping one underlying table. Which governance feature best matches?", options: ["Dynamic Data Masking", "Warehouse auto-suspend", "Search Optimization", "File format objects"], answer: 0, explanation: "Masking policies can return different representations of a value based on role/context while retaining a single governed column.", wrongWhy: "Compute and performance features do not enforce role-aware presentation of sensitive column values." }
  ],
  cheatSheets: [
    { title: "Warehouse scaling", tag: "Performance", body: "Scale up for heavier individual queries. Scale out with multi-cluster capacity when concurrency and queueing are the primary constraint." },
    { title: "Caches at a glance", tag: "Performance", body: "Result cache can avoid re-execution for eligible repeated queries. Warehouse-local cache helps reuse scanned data while compute remains warm." },
    { title: "Time Travel vs Fail-safe", tag: "Architecture", body: "Time Travel is user-accessible historical data protection within configured retention. Fail-safe is a Snowflake-managed recovery period, not a user query feature." },
    { title: "COPY vs Snowpipe", tag: "Loading", body: "COPY INTO is commonly used for controlled/batch loading. Snowpipe automates continuous file ingestion as files arrive." },
    { title: "RBAC rule", tag: "Governance", body: "Prefer least privilege: grant required privileges to roles, then assign roles to users. Avoid broad account roles for routine access." },
    { title: "Share vs clone", tag: "Collaboration", body: "Clone creates an object copy within your environment. Secure sharing exposes governed data to consumers without conventional data export copies." }
  ],
  community: [
    { type: "Common Mistake", domain: "Performance", title: "Bigger warehouses do not solve every slow-query problem", text: "Identify whether the bottleneck is scan volume, query design, concurrency, or compute before resizing." },
    { type: "Exam Tip", domain: "Governance", title: "Separate ownership from access", text: "Questions often test whether a role needs OWNERSHIP or only USAGE/SELECT. Look for least-privilege wording." },
    { type: "Study Strategy", domain: "Loading", title: "Learn ingestion as a decision tree", text: "Be able to distinguish batch COPY, automated file ingestion, and streaming patterns from the scenario cues." },
    { type: "Deep Dive", domain: "Architecture", title: "Know what each architecture layer actually does", text: "A surprising number of distractors swap compute, storage, and cloud-services responsibilities." }
  ],
  resources: [
    { category: "Exam Facts", title: "COF-C03 blueprint walkthrough", description: "Understand domain weights and how to turn the blueprint into a study plan." },
    { category: "Study Strategy", title: "30-day SnowPro Core plan", description: "A structured four-week sequence combining lessons, practice, mistakes and mock exams." },
    { category: "Domain Guide", title: "Performance optimization deep dive", description: "Pruning, Query Profile, warehouses, clustering, caching and optimization decisions." },
    { category: "Technical Guide", title: "Streams, Tasks and Dynamic Tables", description: "A comparison guide focused on exam decision patterns rather than syntax memorization." }
  ]
};
