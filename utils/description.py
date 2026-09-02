EMERGENCY_IMAGE_URL = "https://commons.wikimedia.org/wiki/Special:Redirect/file/Paul_Herrera_Conducts_Flood_Rescue.jpg"
EMERGENCY_IMAGE_SOURCE_URL = "https://commons.wikimedia.org/wiki/File:Paul_Herrera_Conducts_Flood_Rescue.jpg"
EMERGENCY_IMAGE_CAPTION = "Flood rescue image by Armymedic519, Wikimedia Commons, CC0/Public Domain."

PAGE_STYLES = """
<style>
    .safesms-lead {
        color: #d0d5dd;
        font-size: 1.1rem;
        line-height: 1.65;
    }

    .safesms-body {
        color: #d0d5dd;
        font-size: 1rem;
        line-height: 1.65;
    }

    .safesms-body strong,
    .safesms-lead strong {
        color: #f2f4f7;
    }

    .safesms-body a {
        color: #7dd3fc;
    }

    .safesms-accent {
        color: #5eead4;
        font-weight: 700;
    }

    .safesms-warning {
        color: #fca5a5;
        font-weight: 700;
    }

    .safesms-note {
        color: #98a2b3;
        font-size: 0.9rem;
        line-height: 1.45;
    }

    .safesms-guide {
        color: #d0d5dd;
        line-height: 1.6;
    }

    .safesms-guide li {
        margin-bottom: 0.35rem;
    }

    .safesms-guide strong {
        color: #f2f4f7;
    }

    .safesms-shot-placeholder {
        border: 1px dashed #98a2b3;
        border-radius: 8px;
        background: rgba(248, 250, 252, 0.08);
        color: #d0d5dd;
        padding: 2rem 1.25rem;
        min-height: 180px;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        font-weight: 600;
    }
</style>
"""

HOME_INTRO = """
<p class="safesms-lead">
    SafeSMS began with a simple question: <strong>what happens when people need safe directions,
    but internet communication is no longer reliable?</strong>
</p>
"""

HOME_STORY_PRIMARY = """
<p class="safesms-body">
    During <strong>floods, wildfires, storms, landslides, conflict situations, and other emergencies</strong>,
    the most important information is often local: which streets are blocked, which areas are dangerous,
    and where people can move to safety. But mobile data, live web maps, social media, and app-based
    communication can become slow, unavailable, or difficult to access at exactly the wrong moment.
</p>

<p class="safesms-body">
    SafeSMS is a prototype of what could later become a mobile phone application. Building a fully
    featured phone app can take time, so this version explores the core idea first where people would already
    have the app installed, with key map layers downloaded ahead of time, including the <strong>city
    boundary</strong>, <strong>grid system</strong>, <strong>road network</strong>, and <strong>basemap</strong>.
</p>

<p class="safesms-body">
    When an emergency happens, the app does not need to send heavy map data. Instead, it sends only the
    latest local update: which grid cells are hazardous and which ones are safe. That update can fit into
    a compact SMS-style message.
</p>
"""

HOME_STORY_SECONDARY = """
<p class="safesms-body">
    The sender would typically be a <strong>dispatcher, emergency response service, city authority,
    humanitarian coordinator, or trusted local organization</strong> with a broader view of the situation.
    They may know which roads are flooded, which neighborhoods should be avoided, where shelters are open,
    or where higher ground is available.
</p>

<p class="safesms-body">
    This prototype was created by <strong><a href="https://www.linkedin.com/in/jedidiah-chibinga">Jedidiah Chibinga</a></strong>,
    <strong><a href="#">Timotej Gabrijan</a></strong>, and <strong><a href="#">Manuel Kreitmair</a></strong> as a proof of
    concept for <span class="safesms-accent">low-bandwidth emergency navigation</span>. The idea is to explore how communities, responders, and local coordinators
    could share useful spatial information through one of the most resilient communication channels we still
    have that is <span class="safesms-warning">text messaging</span>.
</p>
"""

INSTRUCTIONS_INTRO = """
<p class="safesms-lead">
    SafeSMS is designed around one key principle: <strong>prepare the heavy map information before it is needed,
    then send only the smallest possible emergency update when conditions change.</strong>
</p>
"""

SENDER_GUIDE = """
<div class="safesms-guide">
    <ul>
        <li>Choose or prepare the city or area of interest.</li>
        <li>Use predownloaded layers such as the city boundary, road network, grid, and basemap.</li>
        <li>Mark grid cells as <strong>hazard zones</strong>, such as flooded streets, blocked areas, or unsafe locations.</li>
        <li>Mark grid cells as <strong>safety zones</strong>, such as shelters, higher ground, or meeting points.</li>
        <li>Autogenerate hazard and safety zones when a quick demo scenario is needed.</li>
        <li>Generate a compact SMS code containing the selected hazard and safety grid IDs.</li>
        <li>Send the code by <strong>text message</strong> to people who need the update.</li>
    </ul>
</div>
"""

RECIPIENT_GUIDE = """
<div class="safesms-guide">
    <ul>
        <li>Paste the received SMS code into the app.</li>
        <li>The app decodes the hazard and safety grid IDs.</li>
        <li>Hazard and safety zones are displayed on the map.</li>
        <li>Select the current user location on the map.</li>
        <li>Choose a transport mode: driving, cycling, or walking.</li>
        <li>The app finds the closest safety zone & compares with the shortest route.</li>
        <li>Follow the recommended route toward safety.</li>
    </ul>
</div>
"""

# SENDER_SCREENSHOT_PLACEHOLDER = """
# <div class="safesms-shot-placeholder">
#     Sender page screenshot will appear here.
# </div>
# """

# RECIPIENT_SCREENSHOT_PLACEHOLDER = """
# <div class="safesms-shot-placeholder">
#     Recipient page screenshot will appear here.
# </div>
# """
