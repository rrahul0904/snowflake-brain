export const VIEW_ID = "v26-reference";

const sections = [
  ["Official Documentation", [
    ["Snowflake Documentation", "Product documentation for Snowflake features, SQL, administration, security, and platform behavior.", "https://docs.snowflake.com/"],
    ["SQL Command Reference", "Syntax and reference material for SQL statements and functions used across Snowflake.", "https://docs.snowflake.com/en/sql-reference"],
    ["Snowpark Developer Guides", "Developer documentation for building applications and data workloads with Snowpark.", "https://docs.snowflake.com/en/developer-guide/snowpark/index"],
    ["Release Notes", "Track Snowflake platform changes and recently delivered capabilities.", "https://docs.snowflake.com/en/release-notes/overview"],
  ]],
  ["Courses & Learning", [
    ["Snowflake University", "Official learning paths, certification preparation, and guided Snowflake training.", "https://learn.snowflake.com/"],
    ["SnowPro Certification", "Certification program information and current SnowPro exam paths.", "https://learn.snowflake.com/en/certifications/"],
  ]],
  ["Developer Resources", [
    ["Snowflake Developers", "Developer examples, platform patterns, and application-building resources.", "https://developers.snowflake.com/"],
    ["Snowflake Labs", "Open-source projects and examples maintained for the Snowflake ecosystem.", "https://github.com/Snowflake-Labs"],
  ]],
];

export default async function mount(container) {
  container.innerHTML = `<main class="v26-page v26-reference-page"><section class="v26-page-intro"><p class="v26-kicker">Reference</p><h1>Resources</h1><p>Official Snowflake references and learning resources to verify platform behavior while you prepare.</p></section>${sections.map(section).join("")}</main>`;
}

function section([title, items]) {
  return `<section class="v26-section v26-resource-section"><div class="v26-section-heading"><h2>${title}</h2></div><div class="v26-resource-grid">${items.map(([name, body, href]) => `<a class="v26-resource-card" href="${href}" target="_blank" rel="noopener noreferrer"><div><h3>${name}</h3><p>${body}</p></div><span>↗</span></a>`).join("")}</div></section>`;
}
