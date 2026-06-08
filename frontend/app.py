"""
Analyst Lens - Streamlit Frontend
AI-Powered Geopolitical Intelligence Platform

Application Flow:
1. Monitor - View intelligence sources, fetch new items
2. Inbox - Review AI-processed items, promote to events
3. Events - Manage events, view timelines
4. Signals - View AI-detected emerging trends
5. Outlooks - Generate 24/48/72h trend briefs
6. Scenarios - Build baseline/upside/downside scenarios
7. Ask - Natural language Q&A over intelligence
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone
from httpx import HTTPStatusError

from api_client import APIClient

st.set_page_config(
    page_title="Analyst Lens",
    page_icon="AL",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Professional CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #4a4a6a;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 1rem;
        border-radius: 0.5rem;
        color: white;
    }
    .signal-critical { background-color: #dc2626; color: white; padding: 0.25rem 0.5rem; border-radius: 0.25rem; }
    .signal-high { background-color: #ea580c; color: white; padding: 0.25rem 0.5rem; border-radius: 0.25rem; }
    .signal-medium { background-color: #ca8a04; color: white; padding: 0.25rem 0.5rem; border-radius: 0.25rem; }
    .signal-low { background-color: #16a34a; color: white; padding: 0.25rem 0.5rem; border-radius: 0.25rem; }
    .source-active { color: #16a34a; }
    .source-error { color: #dc2626; }
    .source-paused { color: #6b7280; }
</style>
""", unsafe_allow_html=True)


def get_client() -> APIClient:
    if "api_client" not in st.session_state:
        st.session_state.api_client = APIClient()
    return st.session_state.api_client


def is_authenticated() -> bool:
    return get_client().token is not None


def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown('<p class="main-header">Analyst Lens</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">Geopolitical Intelligence for Banking Risk Management</p>', unsafe_allow_html=True)

        client = get_client()

        if not client.health_check():
            st.error("Cannot connect to API server. Please ensure the backend is running at http://localhost:8000")
            st.stop()

        st.info("Demo credentials: **demo@analyst-lens.local** / **demo123**")

        tab1, tab2 = st.tabs(["Login", "Register"])

        with tab1:
            with st.form("login_form"):
                email = st.text_input("Email", value="demo@analyst-lens.local")
                password = st.text_input("Password", type="password", value="demo123")
                submitted = st.form_submit_button("Login", use_container_width=True)

                if submitted:
                    if email and password:
                        try:
                            client.login(email, password)
                            st.session_state.user = client.get_me()
                            st.rerun()
                        except HTTPStatusError:
                            st.error("Invalid credentials")
                    else:
                        st.warning("Please enter email and password")

            st.divider()
            st.markdown("**Quick Links:** [API Documentation](http://localhost:8000/docs)")

        with tab2:
            with st.form("register_form"):
                reg_email = st.text_input("Email", key="reg_email")
                reg_password = st.text_input("Password", type="password", key="reg_password")
                reg_name = st.text_input("Full Name", key="reg_name")
                reg_role = st.selectbox("Role", ["analyst", "senior_analyst", "admin"], key="reg_role")
                reg_submitted = st.form_submit_button("Register", use_container_width=True)

                if reg_submitted:
                    if reg_email and reg_password and reg_name:
                        try:
                            client.register(reg_email, reg_password, reg_name, reg_role)
                            st.success("Registration successful! Please login.")
                        except HTTPStatusError as e:
                            if e.response.status_code == 409:
                                st.error("Email already registered")
                            else:
                                st.error(f"Registration failed: {e.response.text}")


def sidebar():
    with st.sidebar:
        st.markdown("### Analyst Lens")

        page = st.radio(
            "Navigation",
            ["Dashboard", "Monitor", "Inbox", "Events", "Stories", "Signals", "Outlooks", "Scenarios", "Ask"],
            label_visibility="collapsed",
        )

        st.divider()

        user = st.session_state.get("user", {})
        st.markdown(f"**{user.get('full_name', 'Analyst')}**")
        st.caption(f"{user.get('email', '')}")
        st.caption(f"Role: {user.get('role', 'analyst').replace('_', ' ').title()}")

        st.divider()

        if st.button("Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

        return page


def dashboard_page():
    st.markdown("## Risk Intelligence Dashboard")
    st.caption("Banking sector geopolitical risk overview - Click any item to drill through")

    client = get_client()

    try:
        events = client.list_events()
        outlooks = client.list_outlooks()
        scenarios = client.list_scenarios()
    except HTTPStatusError:
        st.error("Failed to load data")
        return

    # Try to get intelligence data
    sources = []
    signals = []
    raw_items = []
    stories = []
    try:
        sources = client.request("GET", "/intelligence/sources")
        signals = client.request("GET", "/intelligence/signals?active_only=true")
        raw_items = client.request("GET", "/intelligence/items?processed=false&limit=100")
        stories = client.request("GET", "/stories")
    except:
        pass

    # =========================================================================
    # TOP METRICS ROW
    # =========================================================================
    st.markdown("### Key Metrics")
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    high_severity_events = [e for e in events if e.get("severity", 0) >= 4]
    critical_events = [e for e in events if e.get("severity", 0) == 5]
    published_stories = [s for s in stories if s.get("status") == "published"]
    pending_stories = [s for s in stories if s.get("status") in ["draft", "review"]]
    unverified_stories = [s for s in stories if not s.get("all_sources_verified")]

    with col1:
        st.metric("Active Sources", len([s for s in sources if s.get("is_active")]),
                 help="Intelligence sources actively being monitored")
    with col2:
        st.metric("Pending Review", len(raw_items),
                 delta=f"{len(raw_items)} items" if raw_items else None,
                 delta_color="inverse",
                 help="Raw items awaiting AI processing")
    with col3:
        st.metric("Total Events", len(events),
                 help="All tracked intelligence events")
    with col4:
        st.metric("Active Signals", len(signals),
                 delta="Action needed" if any(not s.get("is_acknowledged") for s in signals) else None,
                 delta_color="inverse",
                 help="AI-detected emerging trends requiring attention")
    with col5:
        st.metric("Published Stories", len(published_stories),
                 help="Verified stories distributed to stakeholders")
    with col6:
        st.metric("High/Critical", f"{len(high_severity_events)}/{len(critical_events)}",
                 delta="Priority" if critical_events else None,
                 delta_color="inverse",
                 help="Severity 4-5 / Severity 5 events")

    st.divider()

    # =========================================================================
    # CRITICAL ALERTS SECTION
    # =========================================================================
    if critical_events or [s for s in signals if s.get("severity") in ["critical", "high"]]:
        st.markdown("### Priority Alerts")
        st.warning("The following items require immediate attention from the Risk team.")

        alert_col1, alert_col2 = st.columns(2)

        with alert_col1:
            st.markdown("#### Critical Events (Severity 5)")
            if critical_events:
                for event in critical_events[:5]:
                    with st.expander(f"**{event['title']}** | {event['region']}", expanded=True):
                        st.markdown(f"**Summary:** {event['summary']}")

                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            st.markdown(f"**Region:** {event['region']}")
                            st.markdown(f"**Country:** {event.get('country', 'N/A')}")
                        with col_b:
                            st.markdown(f"**Theme:** {event['theme']}")
                            st.markdown(f"**Sector:** {event.get('sector', 'N/A')}")
                        with col_c:
                            st.markdown(f"**Confidence:** {event['confidence']:.0%}")
                            st.markdown(f"**Occurred:** {event['occurred_at'][:10]}")

                        # Show sources
                        if event.get("sources"):
                            st.markdown("**Sources:**")
                            for src in event["sources"]:
                                src_name = src.get("name", "Unknown") if isinstance(src, dict) else str(src)
                                st.caption(f"  - {src_name}")

                        # Banking implications
                        st.markdown("---")
                        st.markdown("**Banking Implications:**")
                        _show_banking_implications(event)
            else:
                st.success("No critical severity events currently tracked.")

        with alert_col2:
            st.markdown("#### High Priority Signals")
            high_signals = [s for s in signals if s.get("severity") in ["critical", "high"]]
            if high_signals:
                for signal in high_signals[:5]:
                    ack_status = "Acknowledged" if signal.get("is_acknowledged") else "Action Needed"
                    ack_color = "green" if signal.get("is_acknowledged") else "red"

                    with st.expander(f"**{signal['title']}** | {signal['region']}", expanded=True):
                        st.markdown(f"**Type:** {signal['signal_type'].replace('_', ' ').title()}")
                        st.markdown(f"**Description:** {signal['description']}")
                        st.markdown(f"**Evidence:** {signal['evidence_summary']}")
                        st.markdown(f"**Key Indicators:** {signal['key_indicators']}")
                        st.markdown(f"**Watch For:** {signal['watch_for']}")

                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.markdown(f"**Confidence:** {signal['confidence']:.0%}")
                        with col_b:
                            if signal.get("is_acknowledged"):
                                st.success(f"Status: {ack_status}")
                            else:
                                st.error(f"Status: {ack_status}")

                        if signal.get("analyst_notes"):
                            st.info(f"**Analyst Notes:** {signal['analyst_notes']}")
            else:
                st.success("No high priority signals currently active.")

        st.divider()

    # =========================================================================
    # RECENT HIGH SEVERITY EVENTS TABLE
    # =========================================================================
    st.markdown("### Recent High Severity Events")
    st.caption("Events with severity 4-5 requiring risk assessment")

    if high_severity_events:
        # Create a detailed table view
        for event in sorted(high_severity_events, key=lambda x: x.get("occurred_at", ""), reverse=True)[:10]:
            severity_colors = {4: "🟠", 5: "🔴"}
            severity_icon = severity_colors.get(event.get("severity", 0), "⚪")
            ai_badge = "🤖" if event.get("is_ai_generated") else "👤"
            pub_badge = "📤" if event.get("is_published") else ""

            with st.expander(
                f"{severity_icon} {ai_badge} {pub_badge} **{event['title']}** | "
                f"{event['region']} | {event['theme'].title()} | "
                f"Severity {event['severity']}/5"
            ):
                # Main content columns
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown(f"### {event['title']}")
                    st.markdown(f"**Summary:** {event['summary']}")

                    st.markdown("---")
                    st.markdown("#### Classification")
                    class_col1, class_col2, class_col3 = st.columns(3)
                    with class_col1:
                        st.markdown(f"**Region:** {event['region']}")
                        st.markdown(f"**Country:** {event.get('country', 'N/A')}")
                    with class_col2:
                        st.markdown(f"**Theme:** {event['theme']}")
                        st.markdown(f"**Sector:** {event.get('sector', 'N/A')}")
                    with class_col3:
                        st.markdown(f"**Risk Type:** {event.get('risk_type', 'N/A')}")
                        st.markdown(f"**Confidence:** {event['confidence']:.0%}")

                    # Tags
                    if event.get("tags"):
                        tags_str = ", ".join([t.get("name", t) if isinstance(t, dict) else str(t) for t in event["tags"]])
                        st.markdown(f"**Tags:** {tags_str}")

                with col2:
                    st.markdown("#### Status")
                    st.markdown(f"**Severity:** {'⭐' * event['severity']}")
                    st.markdown(f"**Occurred:** {event['occurred_at'][:16]}")
                    st.markdown(f"**Created:** {event['created_at'][:16]}")

                    if event.get("is_published"):
                        st.success("Published to stakeholders")
                    else:
                        st.warning("Not yet published")

                    if event.get("is_ai_generated"):
                        st.info("AI Generated")
                    else:
                        st.info("Manual Entry")

                # Sources section
                st.markdown("---")
                st.markdown("#### Sources")
                sources_list = event.get("sources", [])
                if sources_list:
                    for src in sources_list:
                        if isinstance(src, dict):
                            src_name = src.get("name", "Unknown")
                            src_url = src.get("url", "")
                            src_reliability = src.get("reliability", 0)
                            st.markdown(f"- **{src_name}** (Reliability: {src_reliability:.0%})")
                            if src_url:
                                st.caption(f"  URL: {src_url}")
                        else:
                            st.markdown(f"- {src}")
                else:
                    st.caption("No sources attached")

                # Timeline section
                timeline = event.get("timeline", [])
                if timeline:
                    st.markdown("---")
                    st.markdown("#### Event Timeline")
                    for entry in timeline[-5:]:
                        entry_icon = "🤖" if entry.get("entry_type") == "ai_update" else "📰" if entry.get("entry_type") == "source_update" else "📝"
                        st.caption(f"{entry_icon} {entry['recorded_at'][:16]}: {entry['description']}")

                # Banking implications
                st.markdown("---")
                st.markdown("#### Banking Sector Implications")
                _show_banking_implications(event)
    else:
        st.info("No high severity events currently tracked. This is a positive indicator for risk posture.")

    st.divider()

    # =========================================================================
    # STORIES WORKFLOW STATUS
    # =========================================================================
    st.markdown("### News Stories Pipeline")
    st.caption("Track stories through the verification and publication workflow")

    story_col1, story_col2, story_col3, story_col4 = st.columns(4)

    draft_stories = [s for s in stories if s.get("status") == "draft"]
    review_stories = [s for s in stories if s.get("status") == "review"]
    approved_stories = [s for s in stories if s.get("status") == "approved"]

    with story_col1:
        st.markdown("#### Draft")
        st.metric("Count", len(draft_stories))
        for story in draft_stories[:3]:
            verified = "✅" if story.get("all_sources_verified") else "⚠️"
            st.caption(f"{verified} {story['headline'][:40]}...")

    with story_col2:
        st.markdown("#### In Review")
        st.metric("Count", len(review_stories))
        for story in review_stories[:3]:
            verified = "✅" if story.get("all_sources_verified") else "⚠️"
            st.caption(f"{verified} {story['headline'][:40]}...")

    with story_col3:
        st.markdown("#### Approved")
        st.metric("Count", len(approved_stories))
        for story in approved_stories[:3]:
            verified = "✅" if story.get("all_sources_verified") else "⚠️"
            st.caption(f"{verified} {story['headline'][:40]}...")

    with story_col4:
        st.markdown("#### Published")
        st.metric("Count", len(published_stories))
        for story in published_stories[:3]:
            st.caption(f"📤 {story['headline'][:40]}...")

    # Blocked stories warning
    blocked = [s for s in stories if s.get("status") == "approved" and not s.get("all_sources_verified")]
    if blocked:
        st.warning(f"**{len(blocked)} approved stories blocked from publishing** - sources need verification")
        for story in blocked:
            st.caption(f"  ⚠️ {story['headline']}")

    st.divider()

    # =========================================================================
    # ANALYTICS CHARTS
    # =========================================================================
    st.markdown("### Intelligence Analytics")

    if events:
        # Row 1: Region and Theme distribution
        chart_col1, chart_col2 = st.columns(2)

        df = pd.DataFrame(events)

        with chart_col1:
            st.markdown("#### Events by Region")
            if "region" in df.columns:
                region_counts = df["region"].value_counts().reset_index()
                region_counts.columns = ["Region", "Count"]
                fig = px.pie(region_counts, values="Count", names="Region", hole=0.4,
                           color_discrete_sequence=px.colors.qualitative.Set2)
                fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)

                # Drill-through: show events for selected region
                selected_region = st.selectbox("Drill into region:", ["Select..."] + list(region_counts["Region"]), key="region_drill")
                if selected_region != "Select...":
                    region_events = [e for e in events if e.get("region") == selected_region]
                    st.markdown(f"**{len(region_events)} events in {selected_region}:**")
                    for e in region_events[:5]:
                        st.caption(f"  - [{e['severity']}/5] {e['title'][:50]}...")

        with chart_col2:
            st.markdown("#### Events by Theme")
            if "theme" in df.columns:
                theme_counts = df["theme"].value_counts().reset_index()
                theme_counts.columns = ["Theme", "Count"]
                fig = px.bar(theme_counts, x="Theme", y="Count", color="Count",
                           color_continuous_scale=["#1a1a2e", "#4a4a6a", "#7a7a9a"])
                fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

                # Drill-through: show events for selected theme
                selected_theme = st.selectbox("Drill into theme:", ["Select..."] + list(theme_counts["Theme"]), key="theme_drill")
                if selected_theme != "Select...":
                    theme_events = [e for e in events if e.get("theme") == selected_theme]
                    st.markdown(f"**{len(theme_events)} events for {selected_theme}:**")
                    for e in theme_events[:5]:
                        st.caption(f"  - [{e['severity']}/5] {e['title'][:50]}...")

        # Row 2: Severity and Timeline
        chart_col3, chart_col4 = st.columns(2)

        with chart_col3:
            st.markdown("#### Severity Distribution")
            if "severity" in df.columns:
                severity_counts = df["severity"].value_counts().sort_index().reset_index()
                severity_counts.columns = ["Severity", "Count"]
                colors = ["#16a34a", "#84cc16", "#ca8a04", "#ea580c", "#dc2626"]
                fig = px.bar(severity_counts, x="Severity", y="Count", color="Severity",
                            color_discrete_sequence=colors)
                fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), showlegend=False,
                                xaxis_title="Severity Level", yaxis_title="Number of Events")
                st.plotly_chart(fig, use_container_width=True)

                # Severity breakdown
                st.markdown("**Severity Breakdown:**")
                for sev in range(5, 0, -1):
                    count = len([e for e in events if e.get("severity") == sev])
                    pct = (count / len(events) * 100) if events else 0
                    st.caption(f"  Level {sev}: {count} events ({pct:.0f}%)")

        with chart_col4:
            st.markdown("#### Events Over Time")
            if "occurred_at" in df.columns:
                df["date"] = pd.to_datetime(df["occurred_at"]).dt.date
                date_counts = df.groupby("date").size().reset_index(name="Count")
                fig = px.line(date_counts, x="date", y="Count", markers=True)
                fig.update_layout(margin=dict(t=20, b=20, l=20, r=20),
                                xaxis_title="Date", yaxis_title="Number of Events")
                st.plotly_chart(fig, use_container_width=True)

        # Row 3: Sector analysis (banking focus)
        st.markdown("#### Sector Impact Analysis")
        if "sector" in df.columns:
            sector_df = df[df["sector"].notna()]
            if not sector_df.empty:
                sector_severity = sector_df.groupby("sector").agg({
                    "severity": ["count", "mean"]
                }).reset_index()
                sector_severity.columns = ["Sector", "Event Count", "Avg Severity"]
                sector_severity = sector_severity.sort_values("Event Count", ascending=False)

                sec_col1, sec_col2 = st.columns(2)
                with sec_col1:
                    fig = px.bar(sector_severity, x="Sector", y="Event Count",
                               color="Avg Severity", color_continuous_scale="Reds")
                    fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
                    st.plotly_chart(fig, use_container_width=True)

                with sec_col2:
                    st.markdown("**Sector Risk Summary:**")
                    for _, row in sector_severity.iterrows():
                        risk_level = "High" if row["Avg Severity"] >= 4 else "Medium" if row["Avg Severity"] >= 3 else "Low"
                        st.markdown(f"**{row['Sector'].title()}:** {int(row['Event Count'])} events, Avg Severity: {row['Avg Severity']:.1f} ({risk_level})")
            else:
                st.info("No sector data available for analysis.")

    else:
        st.info("No events yet. Go to **Monitor** to fetch intelligence from sources.")

    st.divider()

    # =========================================================================
    # RECENT ACTIVITY FEED
    # =========================================================================
    st.markdown("### Recent Activity")

    activity_col1, activity_col2 = st.columns(2)

    with activity_col1:
        st.markdown("#### Latest Events")
        recent_events = sorted(events, key=lambda x: x.get("created_at", ""), reverse=True)[:5]
        for event in recent_events:
            severity_colors = {1: "🟢", 2: "🟡", 3: "🟠", 4: "🔴", 5: "⚫"}
            sev_icon = severity_colors.get(event.get("severity", 0), "⚪")
            st.markdown(f"{sev_icon} **{event['title'][:50]}...**")
            st.caption(f"   {event['region']} | {event['theme']} | {event['created_at'][:16]}")

    with activity_col2:
        st.markdown("#### Latest Stories")
        recent_stories = sorted(stories, key=lambda x: x.get("created_at", ""), reverse=True)[:5]
        for story in recent_stories:
            status_icons = {"draft": "📄", "review": "📝", "approved": "✅", "published": "📤"}
            status_icon = status_icons.get(story.get("status", ""), "📄")
            st.markdown(f"{status_icon} **{story['headline'][:50]}...**")
            st.caption(f"   {story['region']} | {story['status'].upper()} | {story['created_at'][:16]}")


def _show_banking_implications(event):
    """Show banking-specific implications for an event."""
    theme = event.get("theme", "").lower()
    region = event.get("region", "")
    severity = event.get("severity", 0)

    implications = {
        "shipping": [
            "Trade Finance: Review Letters of Credit for affected routes",
            "Documentary Collections: Monitor for processing delays",
            "Insurance: Verify cargo coverage remains valid",
            "Client Advisory: Proactive outreach to shipping/trading clients"
        ],
        "sanctions": [
            "Compliance: Immediate sanctions screening review required",
            "KYC: Update due diligence on affected counterparties",
            "Correspondent Banking: Assess secondary sanctions exposure",
            "Reporting: Prepare regulatory notification if required"
        ],
        "cyber": [
            "IT Security: Review system connections to affected infrastructure",
            "Third Parties: Assess vendor exposure",
            "Business Continuity: Verify backup systems operational",
            "Incident Response: Prepare for potential secondary attacks"
        ],
        "conflict": [
            "Country Risk: Update risk ratings for affected region",
            "Credit Exposure: Review all lending to affected area",
            "Provisions: Assess need for credit loss provisions",
            "Client Safety: Confirm status of operations in region"
        ],
        "energy": [
            "Commodity Finance: Review energy sector exposure",
            "Collateral: Monitor commodity price impacts",
            "Credit Risk: Reassess energy sector client creditworthiness",
            "Hedging: Review hedge effectiveness"
        ],
        "trade": [
            "Trade Finance Portfolio: Review affected trade corridors",
            "Tariff Impact: Assess client exposure to trade barriers",
            "Supply Chain: Monitor client supply chain disruptions",
            "Working Capital: Clients may need additional support"
        ]
    }

    # Get relevant implications
    theme_implications = implications.get(theme, [
        f"Monitor developments in {region}",
        "Review client and country exposure",
        "Update risk assessments as needed"
    ])

    # Add severity-based urgency
    if severity >= 4:
        st.error("**Immediate Action Required:**")
    else:
        st.info("**Recommended Actions:**")

    for impl in theme_implications:
        st.markdown(f"- {impl}")

    # Netherlands-specific note
    if region in ["Europe", "Netherlands"] or "dutch" in str(event).lower():
        st.warning("**Netherlands Impact:** Direct relevance to Dutch banking operations. Consider DNB reporting requirements.")


def monitor_page():
    st.markdown("## Intelligence Monitor")
    st.caption("Configure and monitor intelligence sources")

    client = get_client()

    tab1, tab2 = st.tabs(["Sources", "Add Source"])

    with tab1:
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("Seed Demo Sources", use_container_width=True):
                try:
                    client.request("POST", "/intelligence/sources/seed-demo")
                    st.success("Demo sources added!")
                    st.rerun()
                except HTTPStatusError as e:
                    st.error(f"Failed: {e.response.text}")

        try:
            sources = client.request("GET", "/intelligence/sources")
        except HTTPStatusError:
            st.error("Failed to load sources")
            return

        if not sources:
            st.info("No sources configured. Click 'Seed Demo Sources' to add Reuters, BBC, and Al Jazeera feeds.")
            return

        for source in sources:
            status_icon = "🟢" if source["status"] == "active" else "🔴" if source["status"] == "error" else "⏸️"

            with st.expander(f"{status_icon} **{source['name']}** | {source['source_type'].upper()} | {source['item_count']} items"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"**URL:** {source['url'] or 'N/A'}")
                    st.markdown(f"**Reliability:** {source['reliability_score']:.0%}")
                with col2:
                    st.markdown(f"**Region:** {source['default_region'] or 'Global'}")
                    st.markdown(f"**Theme:** {source['default_theme'] or 'General'}")
                with col3:
                    st.markdown(f"**Last Checked:** {source['last_checked_at'][:16] if source['last_checked_at'] else 'Never'}")
                    if source['last_error']:
                        st.error(f"Error: {source['last_error'][:100]}")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Fetch Now", key=f"fetch_{source['id']}", use_container_width=True):
                        with st.spinner("Fetching..."):
                            try:
                                result = client.request("POST", f"/intelligence/sources/{source['id']}/fetch")
                                st.success(f"Fetched {result['items_new']} new items")
                                st.rerun()
                            except HTTPStatusError as e:
                                st.error(f"Fetch failed: {e.response.text}")
                with col2:
                    if st.button("Delete", key=f"delete_{source['id']}", use_container_width=True):
                        try:
                            client.request("DELETE", f"/intelligence/sources/{source['id']}")
                            st.success("Source deleted")
                            st.rerun()
                        except HTTPStatusError as e:
                            st.error(f"Delete failed: {e.response.text}")

    with tab2:
        with st.form("add_source_form"):
            st.markdown("### Add Intelligence Source")

            name = st.text_input("Source Name", placeholder="e.g., Reuters World News")
            source_type = st.selectbox("Type", ["rss", "api", "manual"])
            url = st.text_input("URL", placeholder="https://feeds.reuters.com/...")

            col1, col2 = st.columns(2)
            with col1:
                default_region = st.selectbox("Default Region",
                    ["Global", "Middle East", "Europe", "Asia Pacific", "Africa", "Americas"])
            with col2:
                default_theme = st.selectbox("Default Theme",
                    ["conflict", "sanctions", "elections", "terrorism", "cyber", "shipping", "energy", "trade"])

            reliability = st.slider("Reliability Score", 0.0, 1.0, 0.7, 0.1)

            if st.form_submit_button("Add Source", use_container_width=True):
                if name and url:
                    try:
                        client.request("POST", "/intelligence/sources", json={
                            "name": name,
                            "source_type": source_type,
                            "url": url,
                            "default_region": default_region,
                            "default_theme": default_theme,
                            "reliability_score": reliability
                        })
                        st.success("Source added!")
                        st.rerun()
                    except HTTPStatusError as e:
                        st.error(f"Failed: {e.response.text}")
                else:
                    st.warning("Please fill in name and URL")


def inbox_page():
    st.markdown("## Intelligence Inbox")
    st.caption("Review AI-analyzed items and promote to events")

    client = get_client()

    # Action buttons
    col1, col2, col3, col4 = st.columns([2, 2, 2, 4])
    with col1:
        if st.button("Process Batch", use_container_width=True):
            with st.spinner("Processing items with AI..."):
                try:
                    result = client.request("POST", "/intelligence/items/process-batch?limit=20&auto_promote=true")
                    st.success(f"Processed {result['items_processed']} items, created {result['events_created']} events")
                    st.rerun()
                except HTTPStatusError as e:
                    st.error(f"Failed: {e.response.text}")

    with col2:
        show_filter = st.selectbox("Show", ["unprocessed", "processed", "all"], label_visibility="collapsed")

    with col3:
        if st.button("Run Signal Detection", use_container_width=True):
            with st.spinner("Analyzing patterns..."):
                try:
                    result = client.request("POST", "/intelligence/signals/detect")
                    st.success(f"Analyzed {result['events_analyzed']} events, detected {result['signals_detected']} signals")
                    st.rerun()
                except HTTPStatusError as e:
                    st.error(f"Failed: {e.response.text}")

    try:
        params = {"limit": 50}
        if show_filter == "unprocessed":
            params["processed"] = "false"
        elif show_filter == "processed":
            params["processed"] = "true"

        items = client.request("GET", "/intelligence/items", params=params)
    except HTTPStatusError:
        st.error("Failed to load items")
        return

    if not items:
        st.info("No items in inbox. Go to **Monitor** to fetch intelligence from sources.")
        return

    st.markdown(f"### {len(items)} Items")

    for item in items:
        status_badge = "✅" if item["is_processed"] else "⏳"
        relevance = "📌" if item.get("is_relevant") else "❓" if item.get("is_relevant") is None else "⊘"
        duplicate = "🔄" if item["is_duplicate"] else ""
        event_link = f"→ Event #{item['event_id']}" if item["event_id"] else ""

        with st.expander(f"{status_badge} {relevance} {duplicate} **{item['title'][:80]}...** | {item['source_name']}"):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"**Content:** {item['content'][:300]}...")
                if item['url']:
                    st.markdown(f"[Read Original]({item['url']})")

                if item['ai_summary']:
                    st.markdown("---")
                    st.markdown(f"**AI Summary:** {item['ai_summary']}")
                    st.markdown(f"**Analysis:** Region: {item['ai_region']} | Theme: {item['ai_theme']} | Severity: {item['ai_severity']}/5 | Confidence: {item['ai_confidence']:.0%}")
                    if item['ai_tags']:
                        st.markdown(f"**Tags:** {', '.join(item['ai_tags'])}")

            with col2:
                st.caption(f"Source: {item['source_name']}")
                st.caption(f"Fetched: {item['fetched_at'][:16]}")
                if item['published_at']:
                    st.caption(f"Published: {item['published_at'][:16]}")

                if event_link:
                    st.success(event_link)

                if not item['is_processed']:
                    if st.button("Process", key=f"proc_{item['id']}", use_container_width=True):
                        with st.spinner("Analyzing..."):
                            try:
                                client.request("POST", f"/intelligence/items/{item['id']}/process")
                                st.rerun()
                            except HTTPStatusError as e:
                                st.error(f"Failed: {e.response.text}")

                if item['is_processed'] and not item['event_id'] and item.get('is_relevant'):
                    if st.button("Promote to Event", key=f"prom_{item['id']}", use_container_width=True):
                        try:
                            result = client.request("POST", f"/intelligence/items/{item['id']}/promote")
                            st.success(f"Created Event #{result['event_id']}")
                            st.rerun()
                        except HTTPStatusError as e:
                            st.error(f"Failed: {e.response.text}")


def signals_page():
    st.markdown("## Early Warning Signals")
    st.caption("AI-detected emerging trends and inflection points")

    client = get_client()

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Run Detection", use_container_width=True):
            with st.spinner("Analyzing event patterns..."):
                try:
                    result = client.request("POST", "/intelligence/signals/detect")
                    st.success(f"Detected {result['signals_detected']} new signals")
                    st.rerun()
                except HTTPStatusError as e:
                    st.error(f"Failed: {e.response.text}")

    try:
        signals = client.request("GET", "/intelligence/signals?active_only=true")
    except HTTPStatusError:
        st.error("Failed to load signals")
        return

    if not signals:
        st.info("No active signals detected. Signals are generated when patterns emerge in event data.")
        return

    # Group by severity
    critical = [s for s in signals if s['severity'] == 'critical']
    high = [s for s in signals if s['severity'] == 'high']
    medium = [s for s in signals if s['severity'] == 'medium']
    low = [s for s in signals if s['severity'] == 'low']

    for severity_group, label, color in [
        (critical, "CRITICAL", "#dc2626"),
        (high, "HIGH", "#ea580c"),
        (medium, "MEDIUM", "#ca8a04"),
        (low, "LOW", "#16a34a")
    ]:
        if severity_group:
            st.markdown(f"### {label} Severity ({len(severity_group)})")
            for signal in severity_group:
                with st.expander(f"**{signal['title']}** | {signal['region']} | Conf: {signal['confidence']:.0%}"):
                    st.markdown(f"**Type:** {signal['signal_type'].replace('_', ' ').title()}")
                    st.markdown(f"**Description:** {signal['description']}")
                    st.markdown(f"**Evidence:** {signal['evidence_summary']}")
                    st.markdown(f"**Key Indicators:** {signal['key_indicators']}")
                    st.markdown(f"**Watch For:** {signal['watch_for']}")
                    st.caption(f"Detected: {signal['detected_at'][:16]} | Expires: {signal['expires_at'][:16] if signal['expires_at'] else 'N/A'}")

                    if not signal['is_acknowledged']:
                        notes = st.text_input("Analyst Notes", key=f"notes_{signal['id']}")
                        if st.button("Acknowledge", key=f"ack_{signal['id']}"):
                            try:
                                client.request("POST", f"/intelligence/signals/{signal['id']}/acknowledge",
                                             params={"notes": notes} if notes else None)
                                st.success("Signal acknowledged")
                                st.rerun()
                            except HTTPStatusError as e:
                                st.error(f"Failed: {e.response.text}")
                    else:
                        st.success("Acknowledged")
                        if signal['analyst_notes']:
                            st.info(f"Notes: {signal['analyst_notes']}")


def events_page():
    st.markdown("## Intelligence Events")
    st.caption("View and manage intelligence events")

    client = get_client()

    tab1, tab2 = st.tabs(["Event List", "Create Event"])

    with tab1:
        # Filters
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            region_filter = st.selectbox("Region", ["All", "Middle East", "Europe", "Asia Pacific", "Africa", "Americas", "Global"])
        with col2:
            theme_filter = st.selectbox("Theme", ["All", "conflict", "sanctions", "elections", "terrorism", "cyber", "shipping", "energy", "trade"])
        with col3:
            severity_filter = st.selectbox("Min Severity", ["All", "1", "2", "3", "4", "5"])
        with col4:
            source_filter = st.selectbox("Source", ["All", "AI Generated", "Manual"])

        try:
            events = client.list_events()
        except HTTPStatusError:
            st.error("Failed to load events")
            return

        # Apply filters
        if region_filter != "All":
            events = [e for e in events if e.get("region") == region_filter]
        if theme_filter != "All":
            events = [e for e in events if e.get("theme") == theme_filter]
        if severity_filter != "All":
            events = [e for e in events if e.get("severity", 0) >= int(severity_filter)]
        if source_filter == "AI Generated":
            events = [e for e in events if e.get("is_ai_generated")]
        elif source_filter == "Manual":
            events = [e for e in events if not e.get("is_ai_generated")]

        if not events:
            st.info("No events found matching filters.")
        else:
            st.markdown(f"### {len(events)} Events")

            for event in events:
                severity = event.get("severity", 1)
                severity_colors = {1: "🟢", 2: "🟡", 3: "🟠", 4: "🔴", 5: "⚫"}
                ai_badge = "🤖" if event.get("is_ai_generated") else "👤"
                pub_badge = "📤" if event.get("is_published") else ""

                with st.expander(f"{severity_colors.get(severity, '⚪')} {ai_badge} {pub_badge} **{event['title']}** | {event['region']} | {event['theme']}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"**Region:** {event['region']}")
                        st.markdown(f"**Country:** {event.get('country') or 'N/A'}")
                        st.markdown(f"**Theme:** {event['theme']}")
                    with col2:
                        st.markdown(f"**Severity:** {severity}/5")
                        st.markdown(f"**Confidence:** {event['confidence']:.0%}")
                        st.markdown(f"**Sector:** {event.get('sector') or 'N/A'}")
                    with col3:
                        st.markdown(f"**Occurred:** {event['occurred_at'][:10]}")
                        st.markdown(f"**Created:** {event['created_at'][:10]}")
                        if event.get('is_ai_generated'):
                            st.caption("Source: AI Generated")
                        else:
                            st.caption("Source: Manual Entry")

                    st.markdown("---")
                    st.markdown(f"**Summary:** {event['summary']}")

                    if event.get("tags"):
                        st.markdown(f"**Tags:** {', '.join([t['name'] if isinstance(t, dict) else t for t in event['tags']])}")

                    # Sources with verification
                    sources = event.get("sources", [])
                    if sources:
                        st.markdown("**Sources:**")
                        for src in sources:
                            src_name = src.get('name', 'Unknown') if isinstance(src, dict) else str(src)
                            src_url = src.get('url', '') if isinstance(src, dict) else ''
                            src_reliability = src.get('reliability', 0.5) if isinstance(src, dict) else 0.5
                            st.caption(f"- {src_name} (Reliability: {src_reliability:.0%})")
                            if src_url:
                                st.caption(f"  [Link]({src_url})")

                    # Timeline
                    timeline = event.get("timeline", [])
                    if timeline:
                        st.markdown("**Timeline:**")
                        for entry in timeline[-5:]:
                            entry_type_icon = "🤖" if entry.get('entry_type') == 'ai_update' else "📰" if entry.get('entry_type') == 'source_update' else "📝"
                            st.caption(f"{entry_type_icon} {entry['recorded_at'][:16]}: {entry['description']}")

    with tab2:
        with st.form("create_event_form"):
            st.markdown("### New Intelligence Event")

            title = st.text_input("Title", placeholder="Brief descriptive title")
            summary = st.text_area("Summary", placeholder="Detailed summary of the event...")

            col1, col2 = st.columns(2)
            with col1:
                region = st.selectbox("Region", ["Middle East", "Europe", "Asia Pacific", "Africa", "Americas", "Global"])
                country = st.text_input("Country (optional)")
                theme = st.selectbox("Theme", ["conflict", "sanctions", "elections", "terrorism", "cyber", "shipping", "energy", "tariffs", "trade", "other"])
                sector = st.selectbox("Sector", [None, "energy", "shipping", "finance", "technology", "manufacturing", "agriculture", "defense"])

            with col2:
                severity = st.slider("Severity", 1, 5, 3)
                confidence = st.slider("Confidence", 0.0, 1.0, 0.7, 0.05)
                occurred_at = st.date_input("Occurred Date")

            tags_input = st.text_input("Tags (comma-separated)", placeholder="shipping, energy, sanctions")

            submitted = st.form_submit_button("Create Event", use_container_width=True)

            if submitted:
                if title and summary:
                    tags = [t.strip() for t in tags_input.split(",") if t.strip()] if tags_input else []
                    try:
                        event_data = {
                            "title": title,
                            "summary": summary,
                            "region": region,
                            "theme": theme,
                            "severity": severity,
                            "confidence": confidence,
                            "occurred_at": datetime.combine(occurred_at, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat(),
                            "tags": tags
                        }
                        if country:
                            event_data["country"] = country
                        if sector:
                            event_data["sector"] = sector

                        client.create_event(**event_data)
                        st.success("Event created successfully!")
                        st.rerun()
                    except HTTPStatusError as e:
                        if e.response.status_code == 409:
                            st.warning("Duplicate event detected")
                        else:
                            st.error(f"Failed to create event: {e.response.text}")
                else:
                    st.warning("Please fill in title and summary")


def outlooks_page():
    st.markdown("## Trend Outlooks (24/48/72 hours)")
    st.caption("AI-generated geopolitical trend briefs")

    client = get_client()

    col1, col2, col3 = st.columns([2, 2, 6])
    with col1:
        if st.button("Generate New Outlooks", use_container_width=True):
            with st.spinner("Generating AI outlooks..."):
                try:
                    client.generate_outlooks([24, 48, 72])
                    st.success("Outlooks generated!")
                    st.rerun()
                except HTTPStatusError as e:
                    st.error(f"Failed to generate: {e.response.text}")

    with col2:
        region_filter = st.selectbox("Filter Region", ["All", "Middle East", "Europe", "Asia Pacific", "Global"])

    try:
        outlooks = client.list_outlooks()
    except HTTPStatusError:
        st.error("Failed to load outlooks")
        return

    if not outlooks:
        st.info("No outlooks generated yet. Click 'Generate New Outlooks' to create trend briefs from recent events.")
        return

    # Group by horizon
    for horizon in [24, 48, 72]:
        horizon_outlooks = [o for o in outlooks if o["horizon_hours"] == horizon]
        if region_filter != "All":
            horizon_outlooks = [o for o in horizon_outlooks if o.get("region") == region_filter]

        if horizon_outlooks:
            st.markdown(f"### {horizon}h Outlook")

            for outlook in horizon_outlooks[-3:]:  # Show latest 3
                status_color = "🟢" if outlook["status"] == "published" else "🟡" if outlook["status"] == "reviewed" else "⚪"

                with st.expander(f"{status_color} **{outlook.get('region', 'Global')} | {outlook.get('theme', 'General')}** | Conf: {outlook['confidence']:.0%}"):
                    if outlook.get('executive_summary'):
                        st.markdown(f"**Executive Summary:** {outlook['executive_summary']}")

                    st.markdown(f"**Expected Developments:**\n{outlook['expected_developments']}")
                    st.markdown(f"**Key Indicators:**\n{outlook['key_indicators']}")
                    st.markdown(f"**Implications:**\n{outlook['implications']}")
                    st.markdown(f"**Rationale:**\n{outlook['rationale']}")

                    col1, col2 = st.columns(2)
                    with col1:
                        if outlook.get('sentiment'):
                            st.info(f"Sentiment: {outlook['sentiment'].title()}")
                        if outlook.get('risk_direction'):
                            st.info(f"Risk Direction: {outlook['risk_direction'].title()}")
                    with col2:
                        st.caption(f"Generated: {outlook['generated_at'][:16]}")
                        st.caption(f"Status: {outlook['status'].title()}")


def scenarios_page():
    st.markdown("## Scenario Builder")
    st.caption("Build baseline, upside, and downside scenarios")

    client = get_client()

    tab1, tab2 = st.tabs(["Scenarios", "Create Scenario"])

    with tab1:
        try:
            scenarios = client.list_scenarios()
        except HTTPStatusError:
            st.error("Failed to load scenarios")
            return

        if not scenarios:
            st.info("No scenarios created yet. Use the Create tab to build your first scenario.")
        else:
            for scenario in scenarios:
                case_type = scenario["case_type"]
                case_colors = {"baseline": "🔵", "upside": "🟢", "downside": "🔴"}
                template_badge = "📋" if scenario.get("is_template") else ""

                with st.expander(f"{case_colors.get(case_type, '⚪')} {template_badge} **{scenario['name']}** | {case_type.upper()}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Time Horizon:** {scenario['time_horizon_hours']}h")
                        if scenario.get("probability"):
                            st.markdown(f"**Probability:** {scenario['probability']:.0%}")
                        st.markdown(f"**Region:** {scenario.get('region') or 'Global'}")
                        st.markdown(f"**Theme:** {scenario.get('theme') or 'General'}")
                    with col2:
                        st.markdown(f"**Created:** {scenario['created_at'][:10]}")
                        if scenario.get('is_template'):
                            st.info("Template")

                    st.markdown("---")
                    if scenario.get('description'):
                        st.markdown(f"**Description:** {scenario['description']}")
                    st.markdown(f"**Triggers:**\n{scenario['triggers']}")
                    if scenario.get('warning_indicators'):
                        st.markdown(f"**Warning Indicators:**\n{scenario['warning_indicators']}")
                    st.markdown(f"**Impacts:**\n{scenario['impacts']}")
                    if scenario.get('operational_impacts'):
                        st.markdown(f"**Operational Impacts:**\n{scenario['operational_impacts']}")
                    if scenario.get('market_impacts'):
                        st.markdown(f"**Market Impacts:**\n{scenario['market_impacts']}")

    with tab2:
        with st.form("create_scenario_form"):
            st.markdown("### New Scenario")

            name = st.text_input("Scenario Name", placeholder="Descriptive scenario name")
            description = st.text_area("Description", placeholder="Brief description of this scenario...")
            case_type = st.selectbox("Case Type", ["baseline", "upside", "downside"])

            col1, col2 = st.columns(2)
            with col1:
                region = st.selectbox("Region", [None, "Middle East", "Europe", "Asia Pacific", "Africa", "Americas", "Global"])
                theme = st.selectbox("Theme", [None, "conflict", "sanctions", "elections", "energy", "shipping", "trade"])
            with col2:
                time_horizon = st.number_input("Time Horizon (hours)", min_value=1, max_value=720, value=72)
                probability = st.slider("Probability (optional)", 0.0, 1.0, 0.5, 0.05)
                use_probability = st.checkbox("Include probability estimate")

            triggers = st.text_area("Triggers", placeholder="What conditions would trigger this scenario...")
            warning_indicators = st.text_area("Warning Indicators", placeholder="Early signs to watch for...")
            impacts = st.text_area("General Impacts", placeholder="Expected impacts...")
            operational_impacts = st.text_area("Operational Impacts (optional)", placeholder="Impact on operations...")
            market_impacts = st.text_area("Market Impacts (optional)", placeholder="Impact on markets...")

            is_template = st.checkbox("Save as template for reuse")

            submitted = st.form_submit_button("Create Scenario", use_container_width=True)

            if submitted:
                if name and triggers and impacts:
                    try:
                        client.create_scenario(
                            name=name,
                            case_type=case_type,
                            triggers=triggers,
                            impacts=impacts,
                            time_horizon_hours=time_horizon,
                            probability=probability if use_probability else None,
                        )
                        st.success("Scenario created!")
                        st.rerun()
                    except HTTPStatusError as e:
                        st.error(f"Failed to create: {e.response.text}")
                else:
                    st.warning("Please fill in name, triggers, and impacts")


def stories_page():
    st.markdown("## News Stories")
    st.caption("Generate and publish redistributable news stories from verified events")

    client = get_client()

    tab1, tab2, tab3 = st.tabs(["Stories", "Generate New", "Verify Sources"])

    with tab1:
        col1, col2 = st.columns([3, 1])
        with col2:
            status_filter = st.selectbox("Status", ["All", "draft", "review", "approved", "published"])
            verified_only = st.checkbox("Verified Sources Only")

        try:
            params = {}
            if status_filter != "All":
                params["status_filter"] = status_filter
            if verified_only:
                params["verified_only"] = "true"
            stories = client.request("GET", "/stories", params=params)
        except HTTPStatusError:
            st.error("Failed to load stories")
            return

        if not stories:
            st.info("No news stories yet. Use the 'Generate New' tab to create stories from events.")
        else:
            for story in stories:
                status_icons = {
                    "draft": "📄",
                    "review": "📝",
                    "approved": "✅",
                    "published": "📤",
                    "archived": "📁"
                }
                verified_badge = "🔒" if story["all_sources_verified"] else "⚠️"
                impact_colors = {
                    "low": "🟢",
                    "medium": "🟡",
                    "high": "🟠",
                    "critical": "🔴"
                }

                with st.expander(
                    f"{status_icons.get(story['status'], '📄')} {verified_badge} "
                    f"{impact_colors.get(story['impact_level'], '')} "
                    f"**{story['headline'][:80]}** | {story['region']}"
                ):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        if story.get("subheadline"):
                            st.markdown(f"*{story['subheadline']}*")
                        st.markdown(f"**Summary:** {story.get('executive_summary') or story['body'][:300]}...")

                        st.markdown("---")
                        st.markdown(f"**Full Story:**\n{story['body']}")

                        if story.get("business_implications"):
                            st.markdown(f"**Business Implications:** {story['business_implications']}")
                        if story.get("recommended_actions"):
                            st.markdown(f"**Recommended Actions:** {story['recommended_actions']}")

                    with col2:
                        st.markdown(f"**Region:** {story['region']}")
                        st.markdown(f"**Theme:** {story['theme']}")
                        st.markdown(f"**Impact:** {story['impact_level'].upper()}")
                        st.markdown(f"**Status:** {story['status'].title()}")

                        if story["all_sources_verified"]:
                            st.success("All sources verified")
                        else:
                            st.warning(story.get("verification_summary", "Unverified sources"))

                        st.caption(f"Created: {story['created_at'][:16]}")
                        if story.get("published_at"):
                            st.caption(f"Published: {story['published_at'][:16]}")

                        # Status workflow buttons
                        current_status = story["status"]

                        if current_status == "draft":
                            if st.button("Submit for Review", key=f"review_{story['id']}", use_container_width=True):
                                try:
                                    client.request("PATCH", f"/stories/{story['id']}/status",
                                                 json={"status": "review"})
                                    st.rerun()
                                except HTTPStatusError as e:
                                    st.error(f"Failed: {e.response.text}")

                        elif current_status == "review":
                            col_a, col_b = st.columns(2)
                            with col_a:
                                if st.button("Approve", key=f"approve_{story['id']}", use_container_width=True):
                                    try:
                                        client.request("PATCH", f"/stories/{story['id']}/status",
                                                     json={"status": "approved"})
                                        st.rerun()
                                    except HTTPStatusError as e:
                                        st.error(f"Failed: {e.response.text}")
                            with col_b:
                                if st.button("Back to Draft", key=f"draft_{story['id']}", use_container_width=True):
                                    try:
                                        client.request("PATCH", f"/stories/{story['id']}/status",
                                                     json={"status": "draft"})
                                        st.rerun()
                                    except HTTPStatusError as e:
                                        st.error(f"Failed: {e.response.text}")

                        elif current_status == "approved":
                            if story["all_sources_verified"]:
                                if st.button("Publish", key=f"publish_{story['id']}", use_container_width=True, type="primary"):
                                    try:
                                        client.request("PATCH", f"/stories/{story['id']}/status",
                                                     json={"status": "published"})
                                        st.success("Story published!")
                                        st.rerun()
                                    except HTTPStatusError as e:
                                        st.error(f"Failed: {e.response.text}")
                            else:
                                st.error("Cannot publish - verify all sources first")

    with tab2:
        st.markdown("### Generate Story from Events")

        try:
            events = client.list_events()
        except HTTPStatusError:
            st.error("Failed to load events")
            return

        if not events:
            st.info("No events available. Create events first from the Intelligence Inbox.")
            return

        # Event selection
        event_options = {f"Event #{e['id']}: {e['title'][:50]}": e['id'] for e in events}
        selected_events = st.multiselect(
            "Select Events to Include",
            options=list(event_options.keys()),
            help="Select one or more events to generate a news story"
        )

        selected_ids = [event_options[e] for e in selected_events]

        if selected_ids:
            # Check verification status
            try:
                ids_str = ",".join(str(i) for i in selected_ids)
                verification = client.request("GET", f"/stories/verification-status?event_ids={ids_str}")

                if verification["all_sources_verified"]:
                    st.success(f"All sources verified: {verification['summary']}")
                else:
                    st.warning(f"Verification needed: {verification['summary']}")
            except HTTPStatusError:
                st.warning("Could not check verification status")

            col1, col2 = st.columns(2)
            with col1:
                include_implications = st.checkbox("Include Business Implications", value=True)
            with col2:
                include_actions = st.checkbox("Include Recommended Actions", value=True)

            if st.button("Generate Story", type="primary", use_container_width=True):
                with st.spinner("Generating news story..."):
                    try:
                        story = client.request("POST", "/stories/generate", json={
                            "event_ids": selected_ids,
                            "include_business_implications": include_implications,
                            "include_recommended_actions": include_actions
                        })
                        st.success(f"Story created: {story['headline']}")
                        st.rerun()
                    except HTTPStatusError as e:
                        st.error(f"Generation failed: {e.response.text}")

    with tab3:
        st.markdown("### Verify Event Sources")

        try:
            events = client.list_events()
        except HTTPStatusError:
            st.error("Failed to load events")
            return

        if not events:
            st.info("No events available.")
            return

        # Select event to verify
        event_options = {f"Event #{e['id']}: {e['title'][:50]}": e['id'] for e in events}
        selected_event = st.selectbox(
            "Select Event",
            options=list(event_options.keys())
        )

        if selected_event:
            event_id = event_options[selected_event]

            try:
                sources = client.request("GET", f"/stories/events/{event_id}/sources")
            except HTTPStatusError:
                st.error("Failed to load sources")
                return

            if not sources:
                st.info("No sources attached to this event.")
            else:
                st.markdown(f"### Sources ({len(sources)})")

                for source in sources:
                    status_icons = {
                        "unverified": "❓",
                        "verified": "✅",
                        "disputed": "⚠️",
                        "retracted": "❌"
                    }
                    icon = status_icons.get(source["verification_status"], "❓")

                    with st.expander(f"{icon} **{source['name']}** | Reliability: {source['reliability']:.0%}"):
                        st.markdown(f"**URL:** {source['url'] or 'N/A'}")
                        st.markdown(f"**Current Status:** {source['verification_status'].upper()}")

                        # Show verification history
                        if source.get("verifications"):
                            st.markdown("**Verification History:**")
                            for v in source["verifications"]:
                                st.caption(
                                    f"- {v['status'].upper()} | {v.get('verification_method', 'N/A')} | "
                                    f"{v['created_at'][:16]}"
                                )
                                if v.get("verification_notes"):
                                    st.caption(f"  Notes: {v['verification_notes']}")

                        # Verification form
                        st.markdown("---")
                        st.markdown("**Add Verification:**")

                        col1, col2 = st.columns(2)
                        with col1:
                            new_status = st.selectbox(
                                "Status",
                                ["verified", "disputed", "retracted", "unverified"],
                                key=f"status_{source['id']}"
                            )
                        with col2:
                            method = st.selectbox(
                                "Method",
                                ["cross-reference", "official_confirmation", "multiple_sources", "primary_source", "other"],
                                key=f"method_{source['id']}"
                            )

                        notes = st.text_area(
                            "Verification Notes",
                            key=f"notes_{source['id']}",
                            placeholder="Evidence or reasoning for verification status..."
                        )
                        verified_url = st.text_input(
                            "Evidence URL (optional)",
                            key=f"url_{source['id']}",
                            placeholder="Link to verification evidence..."
                        )

                        if st.button("Submit Verification", key=f"verify_{source['id']}", use_container_width=True):
                            try:
                                client.request("POST", f"/stories/sources/{source['id']}/verify", json={
                                    "source_id": source["id"],
                                    "status": new_status,
                                    "verification_method": method,
                                    "verification_notes": notes,
                                    "verified_url": verified_url if verified_url else None
                                })
                                st.success(f"Source marked as {new_status}")
                                st.rerun()
                            except HTTPStatusError as e:
                                st.error(f"Failed: {e.response.text}")


def ask_page():
    st.markdown("## Ask Anything")
    st.caption("Natural language Q&A over intelligence data")

    client = get_client()

    with st.form("ask_form"):
        question = st.text_area("Your Question", placeholder="What is the current risk outlook for shipping in the Middle East?")
        submitted = st.form_submit_button("Ask", use_container_width=True)

        if submitted and question:
            with st.spinner("Analyzing intelligence..."):
                try:
                    result = client.request("POST", "/ask", json={"question": question})

                    st.markdown("### Answer")
                    st.markdown(result["answer"])

                    st.divider()

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Confidence", f"{result['confidence']:.0%}")
                    with col2:
                        if result.get('sentiment'):
                            st.metric("Sentiment", result['sentiment'].title())
                    with col3:
                        if result.get('sources_cited'):
                            st.metric("Sources", len(result['sources_cited']))

                    if result.get('risk_assessment'):
                        st.info(f"**Risk Assessment:** {result['risk_assessment']}")

                    if result.get('sources_cited'):
                        st.markdown("**Sources:**")
                        for source in result['sources_cited']:
                            st.caption(f"- {source}")

                except HTTPStatusError as e:
                    st.error(f"Failed: {e.response.text}")

    # Q&A History
    st.divider()
    st.markdown("### Recent Questions")

    try:
        history = client.request("GET", "/ask/history?limit=10")
        for item in history:
            with st.expander(f"**{item['question'][:80]}...** | Conf: {item['confidence']:.0%}"):
                st.markdown(item['answer'])
                st.caption(f"Asked: {item['created_at'][:16]}")
    except HTTPStatusError:
        st.caption("No previous questions")


def main():
    if not is_authenticated():
        login_page()
        return

    page = sidebar()

    if page == "Dashboard":
        dashboard_page()
    elif page == "Monitor":
        monitor_page()
    elif page == "Inbox":
        inbox_page()
    elif page == "Events":
        events_page()
    elif page == "Stories":
        stories_page()
    elif page == "Signals":
        signals_page()
    elif page == "Outlooks":
        outlooks_page()
    elif page == "Scenarios":
        scenarios_page()
    elif page == "Ask":
        ask_page()


if __name__ == "__main__":
    main()

