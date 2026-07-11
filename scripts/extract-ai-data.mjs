#!/usr/bin/env node
/**
 * Extract AI tool and blog data from ~/ai-tool-hub/app/data/ 
 * and generate clean Astro-compatible data files.
 */
import fs from 'fs';
import path from 'path';

const SOURCE_TOOLS = path.resolve('/home/edi/ai-tool-hub/app/data/tools.ts');
const SOURCE_BLOG = path.resolve('/home/edi/ai-tool-hub/app/data/blog-posts.ts');
const DEST_TOOLS = path.resolve('/home/edi/ai-tools-astro/src/data/tools.ts');
const DEST_BLOG = path.resolve('/home/edi/ai-tools-astro/src/data/blog-posts.ts');

// ---------- Step 1: Parse the tools.ts file ----------
const toolsSrc = fs.readFileSync(SOURCE_TOOLS, 'utf-8');

// Extract the ToolData interface (not needed for output, just validation)
// Extract ALL_TOOLS array - the data starts after the interface definitions
// Strategy: find the ALL_TOOLS array and manually parse each object

// Find where the ALL_TOOLS export starts
const allToolsMatch = toolsSrc.match(/export\s+const\s+ALL_TOOLS\s*:\s*ToolData\[\]\s*=\s*\[([\s\S]*)\];/);
if (!allToolsMatch) {
  console.error('Could not find ALL_TOOLS array in tools.ts');
  process.exit(1);
}

const arrayContent = allToolsMatch[1];

// Now parse individual tool objects. We need to handle nested braces.
function parseToolObjects(content) {
  const tools = [];
  let i = 0;
  
  while (i < content.length) {
    // Skip whitespace and comments
    const trimmed = content.slice(i).trimStart();
    const skipped = content.length - trimmed.length;
    i += skipped;
    
    if (i >= content.length) break;
    
    // Skip comments
    if (content[i] === '/' && content[i+1] === '/') {
      const nlIdx = content.indexOf('\n', i);
      if (nlIdx === -1) break;
      i = nlIdx + 1;
      continue;
    }
    
    // Must start with {
    if (content[i] !== '{') {
      // Skip any non-object tokens
      if (content[i] === ']' || content[i] === ';') break;
      i++;
      continue;
    }
    
    // Find matching closing brace considering nested braces and strings
    let depth = 0;
    let inString = false;
    let stringChar = null;
    let start = i;
    let j = i;
    
    while (j < content.length) {
      const ch = content[j];
      
      if (inString) {
        if (ch === '\\') {
          j += 2; // skip escaped char
          continue;
        }
        if (ch === stringChar) {
          inString = false;
        }
      } else {
        if (ch === '"' || ch === "'" || ch === '`') {
          inString = true;
          stringChar = ch;
        } else if (ch === '{') {
          depth++;
        } else if (ch === '}') {
          depth--;
          if (depth === 0) {
            // Found the end
            const objStr = content.slice(start, j + 1);
            try {
              // Evaluate the object using Function constructor
              // First, we need to handle the object as a JS expression
              // Replace property names without quotes
              tools.push(evaluateObject(objStr));
            } catch (e) {
              console.error(`Failed to parse tool object at position ${start}:`, e.message);
            }
            i = j + 1;
            break;
          }
        }
      }
      j++;
    }
    
    if (depth !== 0) {
      console.error(`Unterminated object starting at position ${start}`);
      break;
    }
  }
  
  return tools;
}

function evaluateObject(objStr) {
  // We need to convert the JS object literal to proper JSON-like structure
  // The tricky parts: unquoted keys, trailing commas, template literals
  
  // Use a VM approach - wrap in a function that returns the object
  const { VM } = await import('vm');
  
  // But we also need to handle the LucideIcon references
  // Since the icon field uses LucideIcon type but we don't need icons,
  // we can replace icon assignments
  let cleaned = objStr;
  
  // Remove icon assignments (icon: MessageSquare, etc)
  cleaned = cleaned.replace(/icon:\s*\w+,?\s*/g, '');
  
  // Wrap in a proper context
  const context = {};
  
  try {
    const result = VM.runInNewContext(`(${cleaned})`, context, { timeout: 1000 });
    return result;
  } catch (e) {
    console.error('VM eval failed, trying manual parse...');
    return manualParse(objStr);
  }
}

function manualParse(objStr) {
  // Manual parsing as a fallback
  const result = {};
  
  // Extract fields using regex (works for simple flat objects with string/array fields)
  const fieldRegex = /(\w+)\s*:\s*(['"`])(.*?)\2/g;
  let match;
  
  // Handle arrays and nested objects more carefully
  // Simple approach: walk character by character
  let i = 0;
  let currentKey = null;
  
  // Skip opening brace
  i = objStr.indexOf('{');
  if (i === -1) return result;
  i++;
  
  const simpleValues = {};
  const arrays = {};
  const objects = {};
  const numberValues = {};
  
  while (i < objStr.length) {
    // Skip whitespace and comments
    const ch = objStr[i];
    if (ch === '/' && objStr[i+1] === '/') {
      const nl = objStr.indexOf('\n', i);
      i = nl === -1 ? objStr.length : nl + 1;
      continue;
    }
    if (ch === '/' && objStr[i+1] === '*') {
      const end = objStr.indexOf('*/', i + 2);
      i = end === -1 ? objStr.length : end + 2;
      continue;
    }
    if (/\s/.test(ch) || ch === ',') {
      i++;
      continue;
    }
    
    // Read key
    if (/[a-zA-Z_$]/.test(ch)) {
      const keyEnd = objStr.slice(i).search(/[\s:]/);
      if (keyEnd === -1) break;
      currentKey = objStr.slice(i, i + keyEnd);
      i = i + keyEnd;
      // Skip colon and whitespace
      while (i < objStr.length && (objStr[i] === ':' || /\s/.test(objStr[i]))) i++;
      
      // Now determine value type
      if (i >= objStr.length) break;
      
      const valCh = objStr[i];
      
      if (valCh === '[') {
        // Array
        const arrEnd = findMatchingBracket(objStr, i, '[', ']');
        const arrStr = objStr.slice(i, arrEnd + 1);
        try {
          // Simple array parse for arrays of strings
          const items = [];
          let ai = 1;
          let currentItem = '';
          let inStr = false;
          let strChar = null;
          
          while (ai < arrStr.length - 1) {
            const ac = arrStr[ai];
            if (inStr) {
              if (ac === '\\') { currentItem += arrStr[ai+1]; ai += 2; continue; }
              if (ac === strChar) { inStr = false; items.push(currentItem); currentItem = ''; }
              else { currentItem += ac; }
            } else {
              if (ac === '"' || ac === "'" || ac === '`') { inStr = true; strChar = ac; }
              else if (ac === ',') { if (currentItem.trim()) items.push(currentItem.trim()); currentItem = ''; }
              else if (!/\s/.test(ac)) { currentItem += ac; }
            }
            ai++;
          }
          if (currentItem.trim()) items.push(currentItem.trim());
          
          arrays[currentKey] = items;
        } catch (e) {
          arrays[currentKey] = [];
        }
        i = arrEnd + 1;
      } else if (valCh === '{') {
        // Nested object - skip it by finding matching brace
        const objEnd = findMatchingBracket(objStr, i, '{', '}');
        const nestedStr = objStr.slice(i, objEnd + 1);
        // For scoreBreakdown and userQuotes, try to parse
        if (currentKey === 'scoreBreakdown') {
          try {
            const sb = {};
            const numRe = /(\w+)\s*:\s*([\d.]+)/g;
            let nm;
            while ((nm = numRe.exec(nestedStr)) !== null) {
              sb[nm[1]] = parseFloat(nm[2]);
            }
            objects[currentKey] = sb;
          } catch (e) {
            objects[currentKey] = {};
          }
        } else if (currentKey === 'userQuotes') {
          // This is actually an array of objects at top level
          // But it starts with { after the key
          // Actually userQuotes is ToolData[...], so at top level it's an array [...]
          // Wait, let's check - it might be an array that starts with [
          // If we see { here, it's the first element of userQuotes array without [ ]
          // No, in the data it's: userQuotes: [{...}, {...}]
          // So it starts with [ -- but if we're here, valCh is {
          // That means this is a different field
          if (currentKey !== 'userQuotes') {
            // Skip nested object
            objects[currentKey] = {};
          }
          i = objEnd + 1;
        } else {
          // Skip any other nested object
          objects[currentKey] = {};
          i = objEnd + 1;
        }
      } else if (valCh === '"' || valCh === "'" || valCh === '`') {
        // String
        const strEnd = findStringEnd(objStr, i, valCh);
        const rawStr = objStr.slice(i + 1, strEnd);
        // Unescape
        const unescaped = rawStr.replace(/\\n/g, '\n').replace(/\\t/g, '\t').replace(/\\"/g, '"').replace(/\\'/g, "'");
        simpleValues[currentKey] = unescaped;
        i = strEnd + 1;
      } else if (/[\d.-]/.test(valCh)) {
        // Number
        const numEnd = objStr.slice(i).search(/[,\s\]}]/);
        const numStr = objStr.slice(i, numEnd === -1 ? undefined : i + numEnd);
        numberValues[currentKey] = parseFloat(numStr);
        i = numEnd === -1 ? objStr.length : i + numEnd;
      } else {
        // Could be a reference (like a variable name) - skip
        const refEnd = objStr.slice(i).search(/[,\s\]}]/);
        i = refEnd === -1 ? objStr.length : i + refEnd;
      }
    } else {
      i++;
    }
    
    // Check for closing brace
    if (objStr[i] === '}') break;
  }
  
  return { ...simpleValues, ...arrays, ...objects, ...numberValues };
}

function findMatchingBracket(str, start, open, close) {
  let depth = 0;
  let inStr = false;
  let strChar = null;
  
  for (let i = start; i < str.length; i++) {
    const ch = str[i];
    
    if (inStr) {
      if (ch === '\\') { i++; continue; }
      if (ch === strChar) inStr = false;
    } else {
      if (ch === '"' || ch === "'" || ch === '`') { inStr = true; strChar = ch; }
      else if (ch === open) depth++;
      else if (ch === close) {
        depth--;
        if (depth === 0) return i;
      }
    }
  }
  return str.length - 1;
}

function findStringEnd(str, start, quote) {
  for (let i = start + 1; i < str.length; i++) {
    if (str[i] === '\\') { i++; continue; }
    if (str[i] === quote) return i;
  }
  return str.length - 1;
}

// Use the vm approach properly
import { createRequire } from 'module';
const require = createRequire(import.meta.url);

const vm = require('vm');

// More robust parsing using VM
function parseToolsWithVM() {
  // Extract the ALL_TOOLS array text
  const arrayStart = toolsSrc.indexOf('[');
  const arrayEnd = toolsSrc.lastIndexOf('];');
  if (arrayStart === -1 || arrayEnd === -1) {
    console.error('Could not find array bounds');
    return [];
  }
  
  const rawArray = toolsSrc.slice(arrayStart, arrayEnd + 1);
  
  // We need to strip the icon fields since they reference lucide-react
  // Also need to handle the TypeScript type annotations and comments
  
  // Create a sanitized version
  let sanitized = rawArray;
  
  // Remove TypeScript type annotations
  sanitized = sanitized.replace(/:\s*\w+(?:<[^>]*>)?(?=\s*[,=])/g, '');
  
  // Remove icon references (icon: SomeIcon,)
  sanitized = sanitized.replace(/icon:\s*\w+(?:,\s*)?/g, '');
  
  // Remove // comments
  sanitized = sanitized.replace(/\/\/[^\n]*\n/g, '\n');
  
  // Remove /* */ comments
  sanitized = sanitized.replace(/\/\*[\s\S]*?\*\//g, '');
  
  // Trailing commas before ]
  sanitized = sanitized.replace(/,\s*\]/g, ']');
  sanitized = sanitized.replace(/,\s*\}/g, '}');
  
  try {
    const result = vm.runInNewContext(sanitized, {}, { timeout: 5000 });
    return Array.isArray(result) ? result : [];
  } catch (e) {
    console.error('VM parse failed:', e.message);
    // Try a more aggressive sanitization
    console.log('Trying more aggressive sanitization...');
    sanitized = sanitized
      .replace(/\b\w+\s*(?=[\[\(])/g, 'null') // function calls
      .replace(/\b(?:as|const|let|var)\s+\w+/g, '');
    try {
      const result = vm.runInNewContext(sanitized, {}, { timeout: 5000 });
      return Array.isArray(result) ? result : [];
    } catch (e2) {
      console.error('Second VM parse attempt failed:', e2.message);
      return [];
    }
  }
}

const tools = parseToolsWithVM();
console.log(`Parsed ${tools.length} tools`);

if (tools.length === 0) {
  console.error('Failed to parse any tools. Writing fallback.');
}

// Process tools - remove icon field, ensure all data types are correct
const processedTools = tools.map(t => {
  const { icon, ...rest } = t;
  return rest;
});

// ---------- Step 2: Generate tools.ts output ----------
function serializeToolData(tools) {
  const lines = [];
  lines.push('export interface ToolData {');
  lines.push('  id: string;');
  lines.push('  name: string;');
  lines.push('  category: string;');
  lines.push('  rating: number;');
  lines.push('  reviewCount: number;');
  lines.push('  description: string;');
  lines.push('  longDescription: string;');
  lines.push('  pros: string[];');
  lines.push('  cons: string[];');
  lines.push('  pricing: string;');
  lines.push('  pricingDetail: string;');
  lines.push('  features: string[];');
  lines.push('  useCase: string;');
  lines.push('  websiteUrl: string;');
  lines.push('  alternatives: string[];');
  lines.push('  scoreBreakdown: {');
  lines.push('    features: number;');
  lines.push('    reviews: number;');
  lines.push('    momentum: number;');
  lines.push('    popularity: number;');
  lines.push('  };');
  lines.push('  userQuotes: {');
  lines.push('    role: string;');
  lines.push('    company: string;');
  lines.push('    quote: string;');
  lines.push('  }[];');
  lines.push('}');
  lines.push('');
  lines.push('export const ALL_TOOLS: ToolData[] = [');
  
  for (let i = 0; i < tools.length; i++) {
    const t = tools[i];
    if (i > 0) lines.push(',');
    lines.push(stringifyTool(t));
  }
  
  lines.push('\n];');
  lines.push('');
  return lines.join('\n');
}

function stringifyTool(t) {
  const parts = [];
  parts.push('  {');
  stringifyField(parts, 'id', t.id, 1);
  stringifyField(parts, 'name', t.name, 1);
  stringifyField(parts, 'category', t.category, 1);
  stringifyField(parts, 'rating', t.rating, 1);
  stringifyField(parts, 'reviewCount', t.reviewCount, 1);
  stringifyField(parts, 'description', t.description, 1);
  stringifyLongField(parts, 'longDescription', t.longDescription, 1);
  stringifyArray(parts, 'pros', t.pros, 1);
  stringifyArray(parts, 'cons', t.cons, 1);
  stringifyField(parts, 'pricing', t.pricing, 1);
  stringifyLongField(parts, 'pricingDetail', t.pricingDetail, 1);
  stringifyArray(parts, 'features', t.features, 1);
  stringifyLongField(parts, 'useCase', t.useCase, 1);
  stringifyField(parts, 'websiteUrl', t.websiteUrl, 1);
  stringifyStringArray(parts, 'alternatives', t.alternatives, 1);
  stringifyScoreBreakdown(parts, 'scoreBreakdown', t.scoreBreakdown, 1);
  stringifyUserQuotes(parts, 'userQuotes', t.userQuotes, 1);
  parts.push('  }');
  return parts.join('\n');
}

function stringifyField(parts, key, value, indent) {
  const pad = '  '.repeat(indent + 1);
  const escaped = typeof value === 'string' ? value.replace(/"/g, '\\"') : value;
  parts.push(`${pad}${key}: "${escaped}",`);
}

function stringifyLongField(parts, key, value, indent) {
  const pad = '  '.repeat(indent + 1);
  // Use template literal for long text to avoid escaping issues
  const escaped = (value || '').replace(/`/g, '\\`').replace(/\${/g, '\\${');
  parts.push(`${pad}${key}: \`${escaped}\`,`);
}

function stringifyArray(parts, key, arr, indent) {
  const pad = '  '.repeat(indent + 1);
  if (!arr || arr.length === 0) {
    parts.push(`${pad}${key}: [],`);
    return;
  }
  parts.push(`${pad}${key}: [`); 
  for (const item of arr) {
    const escaped = (item || '').replace(/"/g, '\\"');
    parts.push(`${pad}  "${escaped}",`);
  }
  parts.push(`${pad}],`);
}

function stringifyStringArray(parts, key, arr, indent) {
  const pad = '  '.repeat(indent + 1);
  if (!arr || arr.length === 0) {
    parts.push(`${pad}${key}: [],`);
    return;
  }
  parts.push(`${pad}${key}: [${arr.map(a => `"${a.replace(/"/g, '\\"')}"`).join(', ')}],`);
}

function stringifyScoreBreakdown(parts, key, sb, indent) {
  const pad = '  '.repeat(indent + 1);
  if (!sb) {
    parts.push(`${pad}${key}: { features: 0, reviews: 0, momentum: 0, popularity: 0 },`);
    return;
  }
  parts.push(`${pad}${key}: { features: ${sb.features || 0}, reviews: ${sb.reviews || 0}, momentum: ${sb.momentum || 0}, popularity: ${sb.popularity || 0} },`);
}

function stringifyUserQuotes(parts, key, quotes, indent) {
  const pad = '  '.repeat(indent + 1);
  if (!quotes || quotes.length === 0) {
    parts.push(`${pad}${key}: [],`);
    return;
  }
  parts.push(`${pad}${key}: [`);
  for (const q of quotes) {
    const role = (q.role || '').replace(/"/g, '\\"');
    const company = (q.company || '').replace(/"/g, '\\"');
    const quote = (q.quote || '').replace(/"/g, '\\"');
    parts.push(`${pad}  { role: "${role}", company: "${company}", quote: "${quote}" },`);
  }
  parts.push(`${pad}],`);
}

// Write tools.ts
const toolsOutput = serializeToolData(processedTools);
fs.writeFileSync(DEST_TOOLS, toolsOutput);
console.log(`Written ${DEST_TOOLS} (${processedTools.length} tools)`);

// ---------- Step 3: Parse blog posts ----------
const blogSrc = fs.readFileSync(SOURCE_BLOG, 'utf-8');

// Extract BLOG_POSTS array
const blogMatch = blogSrc.match(/export\s+const\s+BLOG_POSTS\s*:\s*BlogPost\[\]\s*=\s*\[([\s\S]*)\];/);
if (!blogMatch) {
  console.error('Could not find BLOG_POSTS array in blog-posts.ts');
  process.exit(1);
}

const blogArrayContent = blogMatch[1];

// Sanitize and parse blog posts
let blogSanitized = blogArrayContent;
// Remove // comments
blogSanitized = blogSanitized.replace(/\/\/[^\n]*\n/g, '\n');
// Trailing commas
blogSanitized = blogSanitized.replace(/,\s*\]/g, ']');
blogSanitized = blogSanitized.replace(/,\s*\}/g, '}');

// Wrap and parse
try {
  const blogResult = vm.runInNewContext(`[${blogSanitized}]`, {}, { timeout: 5000 });
  const blogPosts = Array.isArray(blogResult) ? blogResult : [];
  console.log(`Parsed ${blogPosts.length} blog posts`);
  
  // Generate blog output
  function serializeBlogPosts(posts) {
    const lines = [];
    lines.push('export interface BlogPost {');
    lines.push('  slug: string;');
    lines.push('  title: string;');
    lines.push('  excerpt: string;');
    lines.push('  content: string;');
    lines.push('  author: string;');
    lines.push('  authorRole: string;');
    lines.push('  date: string;');
    lines.push('  category: string;');
    lines.push('  readTime: number;');
    lines.push('  tags: string[];');
    lines.push('}');
    lines.push('');
    lines.push('export const BLOG_POSTS: BlogPost[] = ['); 
    
    for (let i = 0; i < posts.length; i++) {
      const p = posts[i];
      const escaped = JSON.stringify(p.content);
      // Use JSON.stringify for clean escaping but remove outer quotes
      // Actually let's write it properly
      if (i > 0) lines.push(',');
      lines.push(stringifyBlogPost(p));
    }
    
    lines.push('\n];');
    lines.push('');
    return lines.join('\n');
  }
  
  function stringifyBlogPost(p) {
    const p2 = [];
    p2.push('{');
    p2.push(`  slug: "${(p.slug || '').replace(/"/g, '\\"')}",`);
    p2.push(`  title: "${(p.title || '').replace(/"/g, '\\"')}",`);
    p2.push(`  excerpt: "${(p.excerpt || '').replace(/"/g, '\\"')}",`);
    
    // Content - use template literals for proper markdown preservation
    p2.push(`  content: \`${(p.content || '').replace(/`/g, '\\`').replace(/\${/g, '\\${')}\`,`);
    
    p2.push(`  author: "${(p.author || '').replace(/"/g, '\\"')}",`);
    p2.push(`  authorRole: "${(p.authorRole || '').replace(/"/g, '\\"')}",`);
    p2.push(`  date: "${(p.date || '').replace(/"/g, '\\"')}",`);
    p2.push(`  readTime: ${p.readTime || 5},`);
    
    // Tags array
    const tags = p.tags || [];
    p2.push(`  tags: [${tags.map(t => `"${t.replace(/"/g, '\\"')}"`).join(', ')}],`);
    
    p2.push('}');
    return p2.join('\n');
  }
  
  const blogOutput = serializeBlogPosts(blogPosts);
  fs.writeFileSync(DEST_BLOG, blogOutput);
  console.log(`Written ${DEST_BLOG} (${blogPosts.length} posts)`);
  
} catch (e) {
  console.error('Failed to parse blog posts:', e.message);
  process.exit(1);
}

console.log('\n✅ Data extraction complete!');
