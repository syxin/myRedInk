<template>
  <!-- 图片画廊模态框 -->
  <div v-if="visible && record" class="modal-fullscreen" @click="$emit('close')">
    <div class="modal-body" @click.stop>
      <!-- 头部区域 -->
      <div class="modal-header">
        <div style="flex: 1;">
          <!-- 标题区域 -->
          <div class="title-section">
            <h3
              class="modal-title"
              :class="{ 'collapsed': !titleExpanded && record.title.length > 80 }"
            >
              {{ record.title }}
            </h3>
            <button
              v-if="record.title.length > 80"
              class="title-expand-btn"
              @click="titleExpanded = !titleExpanded"
            >
              {{ titleExpanded ? '收起' : '展开' }}
            </button>
          </div>

          <div class="modal-meta">
            <span>{{ record.outline.pages.length }} 张图片 · {{ formattedDate }}</span>
            <button
              class="view-outline-btn"
              @click="$emit('showOutline')"
              title="查看完整大纲"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
              </svg>
              查看大纲
            </button>
          </div>
        </div>

        <div class="header-actions">
          <button class="btn download-btn" @click="$emit('downloadAll')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            打包下载
          </button>
          <button class="close-icon" @click="$emit('close')">×</button>
        </div>
      </div>

      <!-- 图片 + 文字内容，共用一个滚动容器 -->
      <div class="modal-scroll">
        <div class="modal-gallery-grid">
        <div
          v-for="(img, idx) in record.images.generated"
          :key="idx"
          class="modal-img-item"
        >
          <div
            class="modal-img-preview"
            v-if="img"
            :class="{ 'regenerating': regeneratingImages.has(idx) }"
          >
            <img
              :src="`/api/images/${record.images.task_id}/${img}`"
              loading="lazy"
              decoding="async"
            />
            <div class="modal-img-overlay">
              <button
                class="modal-overlay-btn"
                @click="$emit('regenerate', idx)"
                :disabled="regeneratingImages.has(idx)"
              >
                <svg class="regenerate-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M23 4v6h-6"></path>
                  <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                </svg>
                {{ regeneratingImages.has(idx) ? '重绘中...' : '重新生成' }}
              </button>
            </div>
          </div>
          <div class="placeholder" v-else>Waiting...</div>

          <div class="img-footer">
            <span>Page {{ idx + 1 }}</span>
            <span
              v-if="img"
              class="download-link"
              @click="$emit('download', img, idx)"
            >
              下载
            </span>
          </div>
        </div>
      </div>

      <!-- 文字内容：标题 / 文案 / 标签 -->
      <div class="modal-content-section">
        <template v-if="hasContent">
          <div class="content-card">
            <div class="content-card-header">
              <h4>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M4 6h16M4 12h16M4 18h10" />
                </svg>
                标题
              </h4>
              <button class="content-copy-btn" @click="copyAllTitles" :class="{ copied: copiedTitles }">
                {{ copiedTitles ? '已复制' : '复制全部' }}
              </button>
            </div>
            <div class="content-titles">
              <div
                v-for="(title, index) in content!.titles"
                :key="index"
                class="content-title-item"
                :class="{ copied: copiedTitleIndex === index }"
                @click="copyOne(title, index)"
              >
                <span class="title-badge">{{ index === 0 ? '推荐' : `备选${index}` }}</span>
                <span class="title-text">{{ title }}</span>
                <span class="copy-hint">{{ copiedTitleIndex === index ? '已复制' : '点击复制' }}</span>
              </div>
            </div>
          </div>

          <div class="content-card" v-if="content!.copywriting">
            <div class="content-card-header">
              <h4>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
                文案
              </h4>
              <button class="content-copy-btn" @click="copyCopywriting" :class="{ copied: copiedCopywriting }">
                {{ copiedCopywriting ? '已复制' : '复制' }}
              </button>
            </div>
            <div class="content-copywriting">
              <p
                v-for="(paragraph, index) in copywritingParagraphs"
                :key="index"
              >{{ paragraph }}</p>
            </div>
          </div>

          <div class="content-card" v-if="content!.tags && content!.tags.length > 0">
            <div class="content-card-header">
              <h4>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
                  <line x1="7" y1="7" x2="7.01" y2="7" />
                </svg>
                标签
              </h4>
              <button class="content-copy-btn" @click="copyAllTags" :class="{ copied: copiedTags }">
                {{ copiedTags ? '已复制' : '复制全部' }}
              </button>
            </div>
            <div class="content-tags">
              <span
                v-for="(tag, index) in content!.tags"
                :key="index"
                class="tag-chip"
                :class="{ copied: copiedTagIndex === index }"
                @click="copyOneTag(tag, index)"
              >#{{ tag }}</span>
            </div>
          </div>
        </template>

        <div v-else class="content-empty">
          <div class="content-empty-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
            </svg>
          </div>
          <div class="content-empty-title">尚未生成标题、文案和标签</div>
          <div class="content-empty-hint">回到「生成结果」页面点击「生成标题、文案和标签」即可补齐。</div>
        </div>
      </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'

/**
 * 图片画廊模态框组件
 *
 * 功能：
 * - 展示历史记录的所有生成图片
 * - 支持重新生成单张图片
 * - 支持下载单张/全部图片
 * - 可展开查看完整大纲
 */

// 定义记录类型
interface ViewingRecord {
  id: string
  title: string
  updated_at: string
  outline: {
    raw: string
    pages: Array<{ type: string; content: string }>
  }
  images: {
    task_id: string
    generated: string[]
  }
  content?: {
    titles: string[]
    copywriting: string
    tags: string[]
  } | null
}

// 定义 Props
const props = defineProps<{
  visible: boolean
  record: ViewingRecord | null
  regeneratingImages: Set<number>
}>()

// 定义 Emits
defineEmits<{
  (e: 'close'): void
  (e: 'showOutline'): void
  (e: 'downloadAll'): void
  (e: 'download', filename: string, index: number): void
  (e: 'regenerate', index: number): void
}>()

// 标题展开状态
const titleExpanded = ref(false)

// 格式化日期
const formattedDate = computed(() => {
  if (!props.record) return ''
  const d = new Date(props.record.updated_at)
  return `${d.getMonth() + 1}/${d.getDate()}`
})

// ========== 生成的标题 / 文案 / 标签 ==========
const content = computed(() => props.record?.content ?? null)
const hasContent = computed(() => {
  const c = content.value
  if (!c) return false
  const hasTitles = Array.isArray(c.titles) && c.titles.length > 0
  const hasCopy = typeof c.copywriting === 'string' && c.copywriting.trim().length > 0
  const hasTags = Array.isArray(c.tags) && c.tags.length > 0
  return hasTitles || hasCopy || hasTags
})

const copywritingParagraphs = computed(() => {
  const raw = content.value?.copywriting ?? ''
  return raw
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean)
})

// 复制状态
const copiedTitles = ref(false)
const copiedCopywriting = ref(false)
const copiedTags = ref(false)
const copiedTitleIndex = ref<number | null>(null)
const copiedTagIndex = ref<number | null>(null)
const copyTimers: number[] = []

function scheduleReset(cb: () => void, ms = 1600) {
  const id = window.setTimeout(() => {
    cb()
    const idx = copyTimers.indexOf(id)
    if (idx !== -1) copyTimers.splice(idx, 1)
  }, ms)
  copyTimers.push(id)
}

async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    // 降级方案：临时 textarea + execCommand
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    try {
      const ok = document.execCommand('copy')
      return ok
    } catch {
      return false
    } finally {
      document.body.removeChild(textarea)
    }
  }
}

async function copyAllTitles() {
  if (!content.value) return
  if (await copyToClipboard(content.value.titles.join('\n'))) {
    copiedTitles.value = true
    scheduleReset(() => { copiedTitles.value = false })
  }
}

async function copyOne(title: string, index: number) {
  if (await copyToClipboard(title)) {
    copiedTitleIndex.value = index
    scheduleReset(() => { copiedTitleIndex.value = null })
  }
}

async function copyCopywriting() {
  if (!content.value) return
  if (await copyToClipboard(content.value.copywriting)) {
    copiedCopywriting.value = true
    scheduleReset(() => { copiedCopywriting.value = false })
  }
}

async function copyAllTags() {
  if (!content.value) return
  const text = content.value.tags.map(t => `#${t}`).join(' ')
  if (await copyToClipboard(text)) {
    copiedTags.value = true
    scheduleReset(() => { copiedTags.value = false })
  }
}

async function copyOneTag(tag: string, index: number) {
  if (await copyToClipboard(`#${tag}`)) {
    copiedTagIndex.value = index
    scheduleReset(() => { copiedTagIndex.value = null })
  }
}

onUnmounted(() => {
  copyTimers.forEach(id => clearTimeout(id))
  copyTimers.length = 0
})
</script>

<style scoped>
/* 全屏模态框遮罩 */
.modal-fullscreen {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.9);
  z-index: 999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

/* 模态框主体 */
.modal-body {
  background: white;
  width: 100%;
  max-width: 1000px;
  height: 90vh;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 头部区域 */
.modal-header {
  padding: 20px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-shrink: 0;
  gap: 20px;
}

/* 标题区域 */
.title-section {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 4px;
}

.modal-title {
  flex: 1;
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  line-height: 1.4;
  color: #1a1a1a;
  word-break: break-word;
  transition: max-height 0.3s ease;
}

.modal-title.collapsed {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

.title-expand-btn {
  flex-shrink: 0;
  padding: 2px 8px;
  background: #f0f0f0;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  color: #666;
  transition: all 0.2s;
  margin-top: 2px;
}

.title-expand-btn:hover {
  background: var(--primary, #ff2442);
  color: white;
}

/* 元信息 */
.modal-meta {
  font-size: 12px;
  color: #999;
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
}

/* 查看大纲按钮 */
.view-outline-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  color: #495057;
  transition: all 0.2s;
}

.view-outline-btn:hover {
  background: var(--primary, #ff2442);
  color: white;
  border-color: var(--primary, #ff2442);
}

/* 头部操作区 */
.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.download-btn {
  padding: 8px 16px;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.close-icon {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
  padding: 0;
  line-height: 1;
}

.close-icon:hover {
  color: #333;
}

/* 图片网格 */
.modal-gallery-grid {
  padding: 20px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 20px;
}

/* 图片 + 文字内容共用的滚动容器 */
.modal-scroll {
  flex: 1;
  overflow-y: auto;
}

/* 单个图片项 */
.modal-img-item {
  display: flex;
  flex-direction: column;
}

/* 图片预览容器 */
.modal-img-preview {
  position: relative;
  width: 100%;
  aspect-ratio: 3/4;
  overflow: hidden;
  border-radius: 8px;
  contain: layout style paint;
}

.modal-img-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 悬浮遮罩 */
.modal-img-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.15s ease-out;
  pointer-events: none;
  will-change: opacity;
}

.modal-img-preview:hover .modal-img-overlay {
  opacity: 1;
  pointer-events: auto;
}

/* 重绘中状态 */
.modal-img-preview.regenerating .modal-img-overlay {
  opacity: 1;
  pointer-events: auto;
}

.modal-img-preview.regenerating .regenerate-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 遮罩层按钮 */
.modal-overlay-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #333;
  transition: background-color 0.2s, color 0.2s, transform 0.1s;
  will-change: transform;
}

.modal-overlay-btn:hover {
  background: var(--primary, #ff2442);
  color: white;
  transform: scale(1.05);
}

.modal-overlay-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

/* 占位符 */
.placeholder {
  width: 100%;
  aspect-ratio: 3/4;
  background: #f5f5f5;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  font-size: 14px;
}

/* 图片底部信息 */
.img-footer {
  margin-top: 8px;
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #666;
}

.download-link {
  cursor: pointer;
  color: var(--primary, #ff2442);
  transition: opacity 0.2s;
}

.download-link:hover {
  opacity: 0.7;
}

/* 响应式 */
@media (max-width: 768px) {
  .modal-fullscreen {
    padding: 20px;
  }

  .modal-gallery-grid {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 12px;
    padding: 12px;
  }
}

/* ========== 文字内容展示区 ========== */
.modal-content-section {
  padding: 0 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.content-card {
  background: #fafafa;
  border: 1px solid #eee;
  border-radius: 10px;
  padding: 16px;
}

.content-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.content-card-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.content-card-header h4 svg {
  color: var(--primary, #ff2442);
}

.content-copy-btn {
  padding: 4px 12px;
  font-size: 12px;
  color: #666;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
}

.content-copy-btn:hover {
  background: var(--primary, #ff2442);
  color: white;
  border-color: var(--primary, #ff2442);
}

.content-copy-btn.copied {
  background: #e6fffb;
  border-color: #13c2c2;
  color: #13c2c2;
}

.content-titles {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.content-title-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: white;
  border: 1px solid #eee;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
  position: relative;
}

.content-title-item:hover {
  background: var(--primary-light, #fff0f2);
  border-color: var(--primary, #ff2442);
}

.content-title-item.copied {
  background: #e6fffb;
  border-color: #13c2c2;
}

.title-badge {
  flex-shrink: 0;
  padding: 2px 8px;
  font-size: 11px;
  border-radius: 4px;
  background: var(--primary, #ff2442);
  color: white;
}

.content-title-item:not(:first-child) .title-badge {
  background: #999;
}

.title-text {
  flex: 1;
  font-size: 14px;
  color: #1a1a1a;
  line-height: 1.5;
  word-break: break-word;
}

.copy-hint {
  font-size: 12px;
  color: #999;
  opacity: 0;
  transition: opacity 0.15s;
  flex-shrink: 0;
}

.content-title-item:hover .copy-hint,
.content-title-item.copied .copy-hint {
  opacity: 1;
}

.content-title-item.copied .copy-hint {
  color: #13c2c2;
}

.content-copywriting {
  font-size: 14px;
  color: #333;
  line-height: 1.75;
  background: white;
  border: 1px solid #eee;
  border-radius: 8px;
  padding: 12px 14px;
  max-height: 260px;
  overflow-y: auto;
  white-space: pre-wrap;
}

.content-copywriting p {
  margin: 0 0 10px;
}

.content-copywriting p:last-child {
  margin-bottom: 0;
}

.content-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-chip {
  padding: 4px 12px;
  font-size: 13px;
  color: var(--primary, #ff2442);
  background: var(--primary-light, #fff0f2);
  border-radius: 100px;
  cursor: pointer;
  transition: all 0.15s;
}

.tag-chip:hover {
  background: var(--primary, #ff2442);
  color: white;
}

.tag-chip.copied {
  background: #13c2c2;
  color: white;
}

.content-empty {
  padding: 24px;
  background: #fafafa;
  border: 1px dashed #e0e0e0;
  border-radius: 10px;
  text-align: center;
  color: #999;
}

.content-empty-icon {
  width: 40px;
  height: 40px;
  margin: 0 auto 8px;
  border-radius: 50%;
  background: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
}

.content-empty-title {
  font-size: 14px;
  color: #666;
  margin-bottom: 4px;
  font-weight: 500;
}

.content-empty-hint {
  font-size: 12px;
  color: #999;
  line-height: 1.5;
}
</style>
