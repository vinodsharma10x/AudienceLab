// Test script for Audio page - Run this in browser console to test the audio generation

// Test data simulating the flow from voice-actor page
const testData = {
  threadId: 'test-thread-123',
  campaignScripts: {
    selected_angle: {
      id: 'angle-1',
      angle: 1,
      category: 'Problem Solution',
      concept: 'Identifies a common problem and presents the product as the solution',
      type: 'positive'
    },
    scripts: [
      {
        script_id: 'script-1',
        hook: 'Are you tired of struggling with complex project management tools that slow you down instead of helping you?',
        body: 'Introducing TaskFlow - the intuitive project management solution that gets your team organized in minutes, not hours. With drag-and-drop simplicity and real-time collaboration, you can finally focus on what matters: getting things done.',
        selected: true
      },
      {
        script_id: 'script-2', 
        hook: 'Stop wasting hours on project management overhead!',
        body: 'TaskFlow eliminates the complexity with smart automation that handles the busy work for you. Your team stays in sync, deadlines are met, and productivity soars. Join thousands of teams who have already made the switch.',
        selected: true
      }
    ]
  },
  selectedVoice: {
    voice_id: 'EXAVITQu4vr4xnSDxMaL',
    name: 'Bella',
    description: 'A young American woman with a clear, confident voice',
    category: 'conversational',
    labels: ['american', 'female', 'young'],
    gender: 'female',
    age: 'young adult',
    accent: 'american',
    use_case: 'conversational'
  },
  selectedActor: {
    filename: 'actor-001.jpg',
    name: 'Sarah Johnson',
    description: 'Professional young woman in business attire',
    category: 'business'
  }
};

// Store test data in localStorage for Audio page
localStorage.setItem('videoAdsState', JSON.stringify({
  step: 'audio',
  data: testData
}));

// Navigate to audio page
window.location.href = '/video-ads/audio';

console.log('Test data set up for Audio page. Navigating now...');
