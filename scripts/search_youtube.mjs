/**
 * Search YouTube for remaining AI tool videos and update youtube.ts.
 * Handles rate limiting properly.
 * 
 * Usage: https_proxy=http://127.0.0.1:7890 node scripts/search_youtube.mjs
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const YOUTUBE_TS = path.resolve(__dirname, '..', 'src', 'data', 'youtube.ts');
const API_KEY = 'AIzaSyAoMzLT49HjP6fN6VYrwwXX9xMgpkKSwYw';
const API_BASE = 'https://www.googleapis.com/youtube/v3/search';

const TOOLS = [
  // AI Writing & Content
  { id: 'chatgpt', query: 'ChatGPT review 2026' },
  { id: 'claude', query: 'Claude AI review 2026' },
  { id: 'jasper', query: 'Jasper AI review 2026' },
  { id: 'grammarly', query: 'Grammarly AI review 2026' },
  { id: 'copy-ai', query: 'Copy.ai review 2026' },
  { id: 'writesonic', query: 'Writesonic review 2026' },
  { id: 'rytr', query: 'Rytr AI review 2026' },
  { id: 'sudowrite', query: 'Sudowrite review 2026' },
  { id: 'frase', query: 'Frase AI review 2026' },
  // AI Image & Design
  { id: 'midjourney', query: 'Midjourney review 2026' },
  { id: 'dall-e-3', query: 'DALL-E 3 review 2026' },
  { id: 'stable-diffusion', query: 'Stable Diffusion review 2026' },
  { id: 'adobe-firefly', query: 'Adobe Firefly review 2026' },
  { id: 'canva-ai', query: 'Canva AI review 2026' },
  { id: 'leonardo-ai', query: 'Leonardo AI review 2026' },
  { id: 'runway', query: 'Runway ML review 2026' },
  { id: 'ideogram', query: 'Ideogram AI review 2026' },
  // AI Code
  { id: 'github-copilot', query: 'GitHub Copilot review 2026' },
  { id: 'cursor', query: 'Cursor AI editor review 2026' },
  { id: 'tabnine', query: 'Tabnine review 2026' },
  { id: 'codeium', query: 'Codeium review 2026' },
  { id: 'replit-ai', query: 'Replit AI review 2026' },
  { id: 'amazon-codewhisperer', query: 'Amazon CodeWhisperer review 2026' },
  { id: 'sourcegraph-cody', query: 'Sourcegraph Cody review 2026' },
  // AI Video & Audio
  { id: 'synthesia', query: 'Synthesia review 2026' },
  { id: 'heygen', query: 'HeyGen review 2026' },
  { id: 'elevenlabs', query: 'ElevenLabs review 2026' },
  { id: 'descript', query: 'Descript review 2026' },
  { id: 'invideo-ai', query: 'Invideo AI review 2026' },
  { id: 'veed-io', query: 'VEED.IO review 2026' },
  // AI Productivity
  { id: 'notion-ai', query: 'Notion AI review 2026' },
  { id: 'otter-ai', query: 'Otter.ai review 2026' },
  { id: 'fireflies-ai', query: 'Fireflies.ai review 2026' },
  { id: 'motion', query: 'Motion app review 2026' },
  { id: 'superhuman-ai', query: 'Superhuman AI review 2026' },
  // AI Automation
  { id: 'zapier-ai', query: 'Zapier AI review 2026' },
  { id: 'make-ai', query: 'Make.com AI review 2026' },
  { id: 'n8n-ai', query: 'n8n AI review 2026' },
  { id: 'airtable-ai', query: 'Airtable AI review 2026' },
  { id: 'bubble-ai', query: 'Bubble AI review 2026' },
  // AI Agent
  { id: 'autogpt', query: 'AutoGPT review 2026' },
  { id: 'crewai', query: 'CrewAI review 2026' },
  { id: 'langchain', query: 'LangChain review 2026' },
  { id: 'autogen', query: 'Microsoft AutoGen review 2026' },
  { id: 'dify', query: 'Dify AI review 2026' },
  { id: 'coze', query: 'Coze AI review 2026' },
];

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function searchYouTube(query, retries = 4) {
  const url = `${API_BASE}?part=snippet&q=${encodeURIComponent(query)}&type=video&maxResults=1&key=${API_KEY}`;
  
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const stdout = execSync(`curl -s -m 15 "${url}"`, {
        encoding: 'utf-8',
        timeout: 20000,
        env: { ...process.env }
      });
      
      const data = JSON.parse(stdout);
      
      if (data.error) {
        const code = data.error.code;
        if (code === 429) {
          const waitTime = 60 * attempt; // increase wait each retry
          console.log(`  ⚠️ 429, waiting ${waitTime}s (attempt ${attempt}/${retries})...`);
          await sleep(waitTime * 1000);
          continue;
        }
        console.log(`  ⚠️ API error ${code}: ${data.error.message}`);
        return null;
      }
      
      if (data.items && data.items.length > 0 && data.items[0].id && data.items[0].id.videoId) {
        return data.items[0].id.videoId;
      }
      return null;
      
    } catch (err) {
      console.log(`  ⚠️ Error: ${err.message.substring(0, 80)}, waiting 5s...`);
      await sleep(5000);
    }
  }
  return null;
}

async function main() {
  console.log('=== YouTube Video Search for ai-tools-astro ===\n');
  
  const results = {};
  let successCount = 0;
  let failCount = 0;
  
  for (let i = 0; i < TOOLS.length; i++) {
    const tool = TOOLS[i];
    const batchNum = Math.floor(i / 5) + 1;
    const inBatchPos = (i % 5) + 1;
    
    process.stdout.write(`[${batchNum}] (${inBatchPos}/5) ${tool.id} -> "${tool.query}"... `);
    
    const videoId = await searchYouTube(tool.query);
    
    if (videoId) {
      results[tool.id] = videoId;
      successCount++;
      console.log(`✅ ${videoId}`);
    } else {
      results[tool.id] = '';
      failCount++;
      console.log('❌ not found');
    }
    
    // Rate limiting: 3s between calls, 8s after every 5th
    if (i < TOOLS.length - 1) {
      if (inBatchPos === 5) {
        console.log(`   --- Batch ${batchNum} done, pause 8s ---`);
        await sleep(8000);
      } else {
        await sleep(3000);
      }
    }
  }
  
  console.log(`\n=== Results: ${successCount} found, ${failCount} not found ===\n`);
  
  // Read current youtube.ts
  let content = fs.readFileSync(YOUTUBE_TS, 'utf-8');
  
  // Update each tool entry
  for (const [toolId, videoId] of Object.entries(results)) {
    const regex = new RegExp(`("${toolId}"\\s*:\\s*)"[^"]*"`);
    const replacement = `$1"${videoId}"`;
    content = content.replace(regex, replacement);
  }
  
  fs.writeFileSync(YOUTUBE_TS, content, 'utf-8');
  console.log('✅ Updated src/data/youtube.ts');
  
  // Print final entries
  console.log('\n=== Final entries for 40 core tools ===');
  for (const tool of TOOLS) {
    console.log(`  "${tool.id}": "${results[tool.id]}"`);
  }
}

main().catch(console.error);
