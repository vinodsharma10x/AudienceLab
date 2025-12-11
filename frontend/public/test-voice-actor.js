// Test Voice Actor Page - Run this in browser console
// This will set up test data and navigate to the voice-actor page

const testScriptData = {
  "campaign_scripts": {
    "selected_angle": {
      "id": "angle_1",
      "angle": 1,
      "category": "Problem Solution",
      "concept": "While others offer theoretical courses, our approach bridges practical business strategy with AI",
      "type": "positive"
    },
    "scripts": [
      {
        "script_id": "script-1",
        "hook": "Ready for real income without leaving your job?",
        "body": "Look, I thought it was impossible too until I discovered how to combine AI with real business strategy. While others sell you courses full of theory you'll never apply, we teach you the exact method that's already generating extra income for professionals like you.",
        "selected": true
      },
      {
        "script_id": "script-2", 
        "hook": "While others teach theory, we teach success.",
        "body": "Do you know what's the difference between a course that works and one that doesn't? Real results. We don't fill your head with technical concepts you'll never use. We show you exactly how to generate your first AI sale in the next few weeks.",
        "selected": true
      }
    ]
  }
};

// Store test data for the voice-actor page
localStorage.setItem('videoAdsTestData', JSON.stringify(testScriptData));

// Navigate to voice-actor page
window.location.href = '/video-ads/voice-actor';

console.log('✅ Test data set for Voice-Actor page. Navigating now...');
