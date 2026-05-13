const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');
const { promisify } = require('util');

const execAsync = promisify(exec);

const MAX_FILE_SIZE = 20 * 1024 * 1024;
const CHUNK_SIZE = 15 * 1024 * 1024;

let openaiInstance = null;

function getOpenAI() {
  if (openaiInstance) return openaiInstance;

  const OpenAI = require('openai');
  openaiInstance = new OpenAI({
    apiKey: process.env.OPENAI_API_KEY,
    baseURL: process.env.OPENAI_API_URL || 'https://api.openai.com/v1',
  });

  return openaiInstance;
}

async function checkFFmpeg() {
  try {
    await execAsync('ffmpeg -version');
    return true;
  } catch {
    return false;
  }
}

async function compressAudio(inputPath, outputPath) {
  const command = `ffmpeg -i "${inputPath}" -vn -acodec libmp3lame -q:a 2 "${outputPath}" -y`;
  await execAsync(command);
  return outputPath;
}

function splitAudioBuffer(buffer, chunkSize) {
  const chunks = [];
  let offset = 0;

  while (offset < buffer.length) {
    const end = Math.min(offset + chunkSize, buffer.length);
    chunks.push(buffer.slice(offset, end));
    offset = end;
  }

  return chunks;
}

function formatSeconds(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

async function transcribeSingleFileWithTimestamps(audioFilePath, chunkOffset = 0) {
  try {
    const openai = getOpenAI();

    const response = await openai.audio.transcriptions.create({
      file: fs.createReadStream(audioFilePath),
      model: 'whisper-1',
      language: 'zh',
      response_format: 'verbose_json',
      temperature: 0,
      timestamp_granularities: ['word', 'segment'],
    });

    const segments = (response.segments || []).map(seg => ({
      id: seg.id,
      start: chunkOffset + (seg.start || 0),
      end: chunkOffset + (seg.end || 0),
      text: seg.text?.trim() || '',
      words: (seg.words || []).map(w => ({
        word: w.word?.trim() || '',
        start: chunkOffset + (w.start || 0),
        end: chunkOffset + (w.end || 0),
      })),
    })).filter(seg => seg.text);

    const fullText = segments.map(s => s.text).join(' ').trim();

    return {
      text: fullText,
      segments,
      duration: response.duration || 0,
      language: response.language || 'zh',
    };
  } catch (error) {
    console.error('OpenAI Whisper 转写错误:', error.message);
    throw error;
  }
}

async function transcribeSingleFile(audioFilePath) {
  const result = await transcribeSingleFileWithTimestamps(audioFilePath);
  return result.text;
}

function mergeTranscriptionResults(results) {
  if (results.length === 0) {
    return { text: '', segments: [], duration: 0, language: 'zh' };
  }

  if (results.length === 1) {
    return results[0];
  }

  let totalDuration = 0;
  const allSegments = [];

  results.forEach((result, index) => {
    allSegments.push(...result.segments);
    totalDuration = Math.max(totalDuration, (result.segments[result.segments.length - 1]?.end || 0));
  });

  allSegments.sort((a, b) => a.start - b.start);

  allSegments.forEach((seg, idx) => {
    seg.id = idx;
  });

  return {
    text: allSegments.map(s => s.text).join(' ').trim(),
    segments: allSegments,
    duration: totalDuration,
    language: results[0].language,
  };
}

async function transcribeWithOpenAI(audioFilePath, withTimestamps = false) {
  const fileStats = fs.statSync(audioFilePath);
  let processingPath = audioFilePath;
  let tempFiles = [];

  try {
    if (fileStats.size > MAX_FILE_SIZE) {
      console.log(`音频文件较大 (${(fileStats.size / 1024 / 1024).toFixed(2)}MB)，尝试压缩...`);

      const hasFFmpeg = await checkFFmpeg();
      if (hasFFmpeg) {
        const compressedPath = path.join(
          path.dirname(audioFilePath),
          `compressed-${path.basename(audioFilePath, path.extname(audioFilePath))}.mp3`
        );

        await compressAudio(audioFilePath, compressedPath);
        tempFiles.push(compressedPath);

        const compressedStats = fs.statSync(compressedPath);
        console.log(`压缩后大小: ${(compressedStats.size / 1024 / 1024).toFixed(2)}MB`);

        if (compressedStats.size <= MAX_FILE_SIZE) {
          if (withTimestamps) {
            return await transcribeSingleFileWithTimestamps(compressedPath);
          }
          return await transcribeSingleFile(compressedPath);
        }

        processingPath = compressedPath;
      } else {
        console.warn('ffmpeg 未安装，无法压缩音频。大文件可能转写失败。');
      }
    }

    const buffer = fs.readFileSync(processingPath);

    if (buffer.length <= MAX_FILE_SIZE) {
      if (withTimestamps) {
        return await transcribeSingleFileWithTimestamps(processingPath);
      }
      return await transcribeSingleFile(processingPath);
    }

    console.log('文件仍然过大，进行分片转写...');

    const chunks = splitAudioBuffer(buffer, CHUNK_SIZE);
    const results = [];

    for (let i = 0; i < chunks.length; i++) {
      const chunkPath = path.join(
        path.dirname(processingPath),
        `chunk-${i}-${Date.now()}.webm`
      );

      fs.writeFileSync(chunkPath, chunks[i]);
      tempFiles.push(chunkPath);

      console.log(`转写分片 ${i + 1}/${chunks.length}...`);
      const chunkResult = await transcribeSingleFileWithTimestamps(chunkPath, i * 300);
      results.push(chunkResult);
    }

    const merged = mergeTranscriptionResults(results);

    if (withTimestamps) {
      return merged;
    }
    return merged.text;
  } catch (error) {
    throw error;
  } finally {
    for (const tempFile of tempFiles) {
      if (fs.existsSync(tempFile)) {
        try {
          fs.unlinkSync(tempFile);
        } catch (e) {
          console.warn('清理临时文件失败:', tempFile);
        }
      }
    }
  }
}

async function transcribeWithLocalWhisper(audioFilePath, withTimestamps = false) {
  try {
    const outputFormat = withTimestamps ? 'json' : 'txt';
    const command = `whisper "${audioFilePath}" --model base --language Chinese --output_format ${outputFormat}`;

    await execAsync(command);

    if (withTimestamps) {
      const jsonFile = audioFilePath.replace(path.extname(audioFilePath), '.json');
      if (fs.existsSync(jsonFile)) {
        const jsonData = JSON.parse(fs.readFileSync(jsonFile, 'utf-8'));
        return {
          text: jsonData.text?.trim() || '',
          segments: (jsonData.segments || []).map(seg => ({
            id: seg.id,
            start: seg.start || 0,
            end: seg.end || 0,
            text: seg.text?.trim() || '',
            words: [],
          })),
          duration: 0,
          language: 'zh',
        };
      }
    }

    const txtFile = audioFilePath.replace(path.extname(audioFilePath), '.txt');
    if (fs.existsSync(txtFile)) {
      const text = fs.readFileSync(txtFile, 'utf-8').trim();
      if (withTimestamps) {
        return {
          text,
          segments: text ? [{ id: 0, start: 0, end: 0, text, words: [] }] : [],
          duration: 0,
          language: 'zh',
        };
      }
      return text;
    }

    throw new Error('Whisper 输出文件未找到');
  } catch (error) {
    console.error('本地 Whisper 转写错误:', error.message);
    throw error;
  }
}

async function transcribeAudio(audioFilePath, withTimestamps = false) {
  if (!fs.existsSync(audioFilePath)) {
    throw new Error('音频文件不存在');
  }

  const stats = fs.statSync(audioFilePath);
  if (stats.size === 0) {
    throw new Error('音频文件为空');
  }

  if (process.env.OPENAI_API_KEY) {
    return await transcribeWithOpenAI(audioFilePath, withTimestamps);
  }

  if (process.env.USE_LOCAL_WHISPER === 'true') {
    return await transcribeWithLocalWhisper(audioFilePath, withTimestamps);
  }

  console.warn('未配置 Whisper 转写服务，跳过转写');
  if (withTimestamps) {
    return { text: '', segments: [], duration: 0, language: 'zh' };
  }
  return '';
}

async function trimAudio(inputPath, outputPath, startTime, endTime) {
  const hasFFmpeg = await checkFFmpeg();
  if (!hasFFmpeg) {
    throw new Error('ffmpeg 未安装，无法裁剪音频');
  }

  const duration = endTime - startTime;
  const command = `ffmpeg -i "${inputPath}" -ss ${startTime} -t ${duration} -vn -acodec copy "${outputPath}" -y`;

  await execAsync(command);
  return outputPath;
}

function formatTime(seconds) {
  return formatSeconds(seconds);
}

module.exports = transcribeAudio;
module.exports.trimAudio = trimAudio;
module.exports.formatTime = formatTime;
module.exports.transcribeWithTimestamps = (filePath) => transcribeAudio(filePath, true);