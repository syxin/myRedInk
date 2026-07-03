<template>
  <!-- 主题输入组合框 -->
  <div class="composer-container">
    <!-- 输入区域 -->
    <div class="composer-input-wrapper">
      <div class="search-icon-static">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M21 21L16.65 16.65M19 11C19 15.4183 15.4183 19 11 19C6.58172 19 3 15.4183 3 11C3 6.58172 6.58172 3 11 3C15.4183 3 19 6.58172 19 11Z" stroke="#999" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
      <textarea
        ref="textareaRef"
        :value="modelValue"
        @input="handleInput"
        class="composer-textarea"
        placeholder="输入主题，例如：秋季显白美甲..."
        @keydown.enter.prevent="handleEnter"
        :disabled="loading"
        rows="1"
      ></textarea>
    </div>

    <!-- 已上传图片预览 -->
    <div v-if="uploadedImages.length > 0" class="uploaded-images-preview">
      <div class="uploaded-images-track" @dragstart.prevent>
      <div
        v-for="(img, idx) in uploadedImages"
        :key="img.preview"
        class="uploaded-image-item"
        :class="{
          'is-dragging': draggingIndex === idx,
          'is-drop-target':
            dragOverIndex === idx && draggingIndex !== null && draggingIndex !== idx
        }"
        :data-drag-index="idx"
        :title="uploadedImages.length > 1 ? `第 ${idx + 1} 张，拖动可调整顺序` : ''"
        @pointerdown="onPointerDown(idx, $event)"
      >
        <img
          :src="img.preview"
          :alt="`图片 ${idx + 1}`"
          draggable="false"
          @dragstart.prevent
        />
        <span v-if="uploadedImages.length > 1" class="order-badge">{{ idx + 1 }}</span>

        <button
          class="remove-image-btn"
          type="button"
          @click.stop="removeImage(idx)"
          @pointerdown.stop
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      </div>
      <div class="upload-hint">
        <template v-if="uploadedImages.length > 1">
          按顺序参考，可拖动图片调整顺序
        </template>
        <template v-else>
          这些图片将用于生成封面和内容参考
        </template>
      </div>
    </div>

    <!-- 工具栏 -->
    <div class="composer-toolbar">
      <div class="toolbar-left">
        <label class="tool-btn" :class="{ 'active': uploadedImages.length > 0 }" title="上传参考图">
          <input
            type="file"
            accept="image/*"
            multiple
            @change="handleImageUpload"
            :disabled="loading"
            style="display: none;"
          />
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <circle cx="8.5" cy="8.5" r="1.5"></circle>
            <polyline points="21 15 16 10 5 21"></polyline>
          </svg>
          <span v-if="uploadedImages.length > 0" class="badge-count">{{ uploadedImages.length }}</span>
        </label>

        <!-- 生成张数设置 -->
        <div class="page-count-control" ref="pageCountRef">
          <button
            type="button"
            class="tool-btn page-count-btn"
            :class="{ 'active': pageCountActive }"
            :title="`设置生成张数：${pageCountActive ? pageCount + ' 张' : '默认'}`"
            :disabled="loading"
            @click="togglePageCountMenu"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="4" width="13" height="16" rx="2"></rect>
              <path d="M8 4v16"></path>
              <path d="M19 8v12a2 2 0 0 1-2 2H8"></path>
            </svg>
            <span class="page-count-label">
              <template v-if="pageCountActive">{{ pageCount }} 张</template>
              <template v-else>张数</template>
            </span>
          </button>

          <div v-if="showPageCountMenu" class="page-count-menu" role="dialog" aria-label="设置生成张数">
            <div class="menu-header">
              <span>生成张数</span>
              <span class="menu-value">{{ pageCountActive ? pageCount + ' 张' : '默认' }}</span>
            </div>
            <div class="quick-options">
              <button
                v-for="opt in quickOptions"
                :key="opt"
                type="button"
                class="quick-option"
                :class="{ active: pageCountActive && pageCount === opt }"
                @click="applyPageCount(opt)"
              >
                {{ opt }}
              </button>
            </div>
            <div class="slider-row">
              <input
                type="range"
                min="1"
                max="18"
                step="1"
                :value="pageCountActive ? pageCount : 8"
                @input="onSliderInput"
                class="page-slider"
                aria-label="拖动调整生成张数"
              />
              <input
                type="number"
                min="1"
                max="30"
                :value="pageCountActive ? pageCount : ''"
                placeholder="自定义"
                @input="onNumberInput"
                class="page-number"
                aria-label="直接输入生成张数"
              />
            </div>
            <div class="menu-footer">
              <button type="button" class="menu-btn ghost" @click="clearPageCount">使用默认</button>
              <button type="button" class="menu-btn primary" @click="closePageCountMenu">完成</button>
            </div>
          </div>
        </div>

        <!-- 分辨率设置 -->
        <div class="resolution-control" ref="resolutionRef">
          <button
            type="button"
            class="tool-btn resolution-btn"
            :class="{ 'active': resolutionActive }"
            :title="`设置图像尺寸：${resolutionLabel}`"
            :disabled="loading"
            @click="toggleResolutionMenu"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2"></rect>
              <path d="M3 9h18"></path>
              <path d="M9 3v18"></path>
            </svg>
            <span class="resolution-label">{{ resolutionLabel }}</span>
          </button>

          <div v-if="showResolutionMenu" class="resolution-menu" role="dialog" aria-label="设置图像尺寸">
            <div class="resolution-header">
              <span class="resolution-title">设置图像尺寸</span>
              <span class="resolution-current">当前：{{ effectiveDimensions || '默认' }}</span>
            </div>

            <!-- 模式切换 -->
            <div class="resolution-tabs">
              <button
                v-for="tab in resolutionTabs"
                :key="tab.id"
                type="button"
                class="resolution-tab"
                :class="{ active: resolutionMode === tab.id }"
                @click="resolutionMode = tab.id"
              >
                {{ tab.label }}
              </button>
            </div>

            <!-- 按比例模式 -->
            <template v-if="resolutionMode === 'ratio'">
              <div class="section-label">基准分辨率</div>
              <div class="size-grid">
                <button
                  v-for="size in baseSizes"
                  :key="size"
                  type="button"
                  class="size-option"
                  :class="{ active: baseSize === size }"
                  @click="baseSize = size"
                >
                  {{ size }}
                </button>
              </div>

              <div class="section-label">图像比例</div>
              <div class="ratio-grid">
                <button
                  v-for="ratio in aspectRatios"
                  :key="ratio.value"
                  type="button"
                  class="ratio-option"
                  :class="{ active: aspectRatio === ratio.value }"
                  @click="aspectRatio = ratio.value"
                >
                  <span class="ratio-icon" :style="ratioIconStyle(ratio.value)"></span>
                  <span class="ratio-text">{{ ratio.label }}</span>
                </button>
              </div>
            </template>

            <!-- 自定义宽高模式 -->
            <template v-else-if="resolutionMode === 'custom'">
              <div class="section-label">自定义宽高（像素）</div>
              <div class="custom-size-row">
                <input
                  type="number"
                  min="256"
                  max="4096"
                  step="64"
                  v-model.number="customWidth"
                  class="custom-input"
                  placeholder="宽"
                  aria-label="自定义宽度"
                />
                <span class="custom-x">×</span>
                <input
                  type="number"
                  min="256"
                  max="4096"
                  step="64"
                  v-model.number="customHeight"
                  class="custom-input"
                  placeholder="高"
                  aria-label="自定义高度"
                />
              </div>
              <div class="custom-hint">建议范围 512~4096，最终以服务商支持的尺寸为准</div>
            </template>

            <!-- 自动模式提示 -->
            <template v-else>
              <div class="auto-hint">
                由系统根据小红书的常用比例自动选择，无需手动设置。
              </div>
            </template>

            <div class="resolution-preview">
              <div class="preview-label">将使用</div>
              <div class="preview-value">{{ effectiveDimensions || '系统默认' }}</div>
            </div>

            <div class="menu-footer">
              <button type="button" class="menu-btn ghost" @click="closeResolutionMenu">取消</button>
              <button type="button" class="menu-btn primary" @click="confirmResolution">确定</button>
            </div>
          </div>
        </div>

        <!-- 依次参考开关：仅当生成张数 == 上传参考图张数时可开启 -->
        <div class="sequential-ref-control" :title="sequentialTooltip">
          <label class="sequential-switch" :class="{ disabled: !canEnableSequential }">
            <input
              type="checkbox"
              :checked="sequentialReference"
              :disabled="!canEnableSequential || loading"
              @change="onSequentialToggle"
            />
            <span class="switch-track"><span class="switch-thumb"></span></span>
            <span class="switch-label">依次参考</span>
          </label>
        </div>
      </div>
      <div class="toolbar-right">
        <button
          class="btn btn-primary generate-btn"
          @click="$emit('generate')"
          :disabled="!modelValue.trim() || loading"
        >
          <span v-if="loading" class="spinner-sm"></span>
          <span v-else>生成大纲</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'

/**
 * 主题输入组合框组件
 *
 * 功能：
 * - 主题文本输入（自动调整高度）
 * - 参考图片上传（最多5张）
 * - 生成按钮
 */

// 定义上传的图片类型
interface UploadedImage {
  file: File
  preview: string
}

// 定义 Props
const props = defineProps<{
  modelValue: string
  loading: boolean
}>()

// 定义 Emits
const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'generate'): void
  (e: 'imagesChange', images: File[]): void
  (e: 'pageCountChange', count: number | null): void
  (e: 'resolutionChange', value: {
    size: string | null            // 像素串，如 "2400x3200"
    image_size: string | null      // 档位名 "1K"/"2K"/"4K"，custom 模式为 null
    aspect_ratio: string | null
  }): void
  (e: 'sequentialReferenceChange', value: boolean): void
}>()

// 输入框引用
const textareaRef = ref<HTMLTextAreaElement | null>(null)

// 已上传的图片
const uploadedImages = ref<UploadedImage[]>([])

// ========== 生成张数控制 ==========
// 张数设置弹窗容器（点击外部关闭）
const pageCountRef = ref<HTMLElement | null>(null)
const showPageCountMenu = ref(false)
// 当前生效的张数（若为 null 则使用默认）
const pageCount = ref(8)
const pageCountActive = ref(false)
// 快捷按钮选项
const quickOptions = [3, 6, 8, 12, 15, 18]

// ========== 依次参考开关 ==========
// 仅当用户主动设置了张数、且张数 == 上传参考图张数时可开启
const sequentialReference = ref(false)
// 记录用户是否在"条件满足"期间手动关闭过；一旦条件跨出满足区间再回来，就重置这个标记。
// 用来避免"用户明确关掉后又被自动重新打开"的骚扰。
const sequentialUserClosed = ref(false)
const canEnableSequential = computed(() => {
  return (
    uploadedImages.value.length > 0 &&
    pageCountActive.value &&
    pageCount.value === uploadedImages.value.length
  )
})
const sequentialTooltip = computed(() => {
  if (uploadedImages.value.length === 0) {
    return '请先上传参考图后再启用「依次参考」'
  }
  if (!pageCountActive.value) {
    return '请先设置生成张数，等于上传参考图张数时可开启'
  }
  if (pageCount.value !== uploadedImages.value.length) {
    return `生成张数 ${pageCount.value} 需与参考图张数 ${uploadedImages.value.length} 一致才能开启`
  }
  return '开启后：第 N 张图片仅使用第 N 张参考图'
})

function onSequentialToggle(event: Event) {
  const target = event.target as HTMLInputElement
  const next = target.checked && canEnableSequential.value
  sequentialReference.value = next
  // 用户主动关闭时记住这个选择；主动开启则清掉标记
  sequentialUserClosed.value = canEnableSequential.value && !next
  emit('sequentialReferenceChange', next)
}

// 参考图张数 / 页数张数变化时同步「依次参考」开关：
// - 条件不再满足 -> 关闭；同时清掉"用户手动关闭"的标记，方便下一次条件重新达成后可以再自动打开
// - 条件满足且用户没有明确关过 -> 自动打开，让用户少一步操作
// - 条件满足但用户已手动关过 -> 保持关闭，尊重用户的选择
function ensureSequentialConsistency() {
  if (!canEnableSequential.value) {
    if (sequentialReference.value) {
      sequentialReference.value = false
      emit('sequentialReferenceChange', false)
    }
    // 条件掉出满足区间，重置手动关闭标记：下次达成时可以再自动打开
    sequentialUserClosed.value = false
    return
  }
  if (!sequentialReference.value && !sequentialUserClosed.value) {
    sequentialReference.value = true
    emit('sequentialReferenceChange', true)
  }
}

function togglePageCountMenu() {
  showPageCountMenu.value = !showPageCountMenu.value
  if (showPageCountMenu.value) {
    // 首次展开时若无有效值，回退到默认 8
    if (!pageCount.value || pageCount.value < 1) {
      pageCount.value = 8
    }
  }
}

function closePageCountMenu() {
  showPageCountMenu.value = false
}

function applyPageCount(count: number) {
  pageCount.value = count
  pageCountActive.value = true
  emit('pageCountChange', count)
  ensureSequentialConsistency()
}

function clearPageCount() {
  pageCountActive.value = false
  pageCount.value = 8
  emit('pageCountChange', null)
  ensureSequentialConsistency()
}

function onSliderInput(event: Event) {
  const value = Number((event.target as HTMLInputElement).value)
  if (value >= 1) {
    pageCount.value = value
    pageCountActive.value = true
    emit('pageCountChange', value)
    ensureSequentialConsistency()
  }
}

function onNumberInput(event: Event) {
  const raw = (event.target as HTMLInputElement).value
  const value = parseInt(raw, 10)
  if (!isNaN(value) && value >= 1) {
    const clamped = Math.min(value, 30)
    pageCount.value = clamped
    pageCountActive.value = true
    emit('pageCountChange', clamped)
    ensureSequentialConsistency()
  }
}

// 点击外部关闭张数 / 分辨率菜单
function handleClickOutside(event: MouseEvent) {
  const target = event.target as Node
  if (
    showPageCountMenu.value &&
    pageCountRef.value &&
    !pageCountRef.value.contains(target)
  ) {
    showPageCountMenu.value = false
  }
  if (
    showResolutionMenu.value &&
    resolutionRef.value &&
    !resolutionRef.value.contains(target)
  ) {
    showResolutionMenu.value = false
  }
}

// 绑定/解绑全局点击监听
if (typeof document !== 'undefined') {
  document.addEventListener('click', handleClickOutside)
  onUnmounted(() => {
    document.removeEventListener('click', handleClickOutside)
  })
}

// ========== 分辨率控制 ==========
const resolutionRef = ref<HTMLElement | null>(null)
const showResolutionMenu = ref(false)

// 三个模式：auto（使用默认）/ ratio（按比例）/ custom（自定义宽高）
type ResolutionMode = 'auto' | 'ratio' | 'custom'
const resolutionMode = ref<ResolutionMode>('ratio')

// ratio 模式：基准分辨率 + 比例
const baseSizes = ['1K', '2K', '4K']
const baseSize = ref('4K')

const aspectRatios = [
  { value: '1:1', label: '1:1' },
  { value: '3:2', label: '3:2' },
  { value: '2:3', label: '2:3' },
  { value: '16:9', label: '16:9' },
  { value: '9:16', label: '9:16' },
  { value: '4:3', label: '4:3' },
  { value: '3:4', label: '3:4' },
  { value: '21:9', label: '21:9' },
]
const aspectRatio = ref('3:4')

// custom 模式：自定义宽高
const customWidth = ref(2400)
const customHeight = ref(3200)

// 用户是否显式设置过（非默认）
const resolutionActive = ref(false)

const resolutionTabs = [
  { id: 'auto' as ResolutionMode, label: '自动' },
  { id: 'ratio' as ResolutionMode, label: '按比例' },
  { id: 'custom' as ResolutionMode, label: '自定义宽高' },
]

// 基准分辨率对应的"长边像素"映射，确保和后端发给生图接口的值完全一致
const baseSizePixelMap: Record<string, number> = {
  '1K': 1024,
  '2K': 2048,
  '4K': 3200,
}

// gpt-image-2 等模型要求宽高都是 16 的倍数，预览和提交都按此对齐
const PIXEL_ALIGNMENT = 16

function alignToStep(value: number, step: number = PIXEL_ALIGNMENT): number {
  const aligned = Math.round(value / step) * step
  return aligned < step ? step : aligned
}

/**
 * 根据「基准分辨率 + 比例」推算出 (width, height)。
 * 规则：长边对齐基准分辨率，短边按比例缩放后再四舍五入到 16 的倍数，
 * 保证 gpt-image 等模型不会因为对齐问题报 invalid_size。
 */
function computeRatioDimensions(base: string, ratio: string): { width: number; height: number } | null {
  const maxPx = baseSizePixelMap[base]
  if (!maxPx) return null
  const parts = ratio.split(':').map(Number)
  if (parts.length !== 2 || !parts[0] || !parts[1]) return null
  const [wRatio, hRatio] = parts
  let width: number
  let height: number
  if (wRatio >= hRatio) {
    const scale = maxPx / wRatio
    width = maxPx
    height = Math.round(hRatio * scale)
  } else {
    const scale = maxPx / hRatio
    width = Math.round(wRatio * scale)
    height = maxPx
  }
  // 两边一起对齐到 16 的倍数
  return {
    width: alignToStep(width),
    height: alignToStep(height),
  }
}

// 当前面板里的实际像素值（ratio 模式按公式推，custom 模式直接读输入框）
const currentDimensions = computed<{ width: number; height: number } | null>(() => {
  if (resolutionMode.value === 'auto') return null
  if (resolutionMode.value === 'custom') {
    if (customWidth.value && customHeight.value) {
      // 自定义宽高同样对齐到 16 的倍数，避免后端被生图接口拒绝
      return {
        width: alignToStep(customWidth.value),
        height: alignToStep(customHeight.value),
      }
    }
    return null
  }
  return computeRatioDimensions(baseSize.value, aspectRatio.value)
})

// 预览展示用："2400×3200" 这种字符串
const effectiveDimensions = computed<string | null>(() => {
  const dims = currentDimensions.value
  return dims ? `${dims.width}×${dims.height}` : null
})

// 按钮上的显示文本
const resolutionLabel = computed(() => {
  // 按钮文案应反映已确认状态：未确认时显示「尺寸」，确认后显示具体值
  if (!resolutionActive.value) return '尺寸'
  const dims = effectiveDimensions.value
  return dims ? dims : '尺寸'
})

// 比例预览图标样式（根据比例给出宽高比）
function ratioIconStyle(ratio: string) {
  const [w, h] = ratio.split(':').map(Number)
  const maxDim = 20
  let width: number, height: number
  if (w >= h) {
    width = maxDim
    height = Math.round((h / w) * maxDim)
  } else {
    height = maxDim
    width = Math.round((w / h) * maxDim)
  }
  return { width: `${width}px`, height: `${height}px` }
}

function toggleResolutionMenu() {
  // 点击外部关闭逻辑与张数共用，这里只切换
  showResolutionMenu.value = !showResolutionMenu.value
  if (showResolutionMenu.value) {
    showPageCountMenu.value = false
    // 打开时若为默认则选中 ratio / 4K / 3:4
    if (!resolutionActive.value) {
      resolutionMode.value = 'ratio'
      baseSize.value = '4K'
      aspectRatio.value = '3:4'
    }
  }
}

function closeResolutionMenu() {
  showResolutionMenu.value = false
}

// 确认分辨率设置
function confirmResolution() {
  if (resolutionMode.value === 'auto') {
    // 自动：恢复默认，不传参数
    resolutionActive.value = false
    emit('resolutionChange', { size: null, image_size: null, aspect_ratio: null })
  } else if (resolutionMode.value === 'ratio') {
    // 后端生图接口需要具体像素串（如 "2400x3200"），而不是 "4K" 这种档位
    const dims = computeRatioDimensions(baseSize.value, aspectRatio.value)
    if (!dims) {
      // 兜底：拿不到尺寸时，仍走默认，避免传一个非法字段
      resolutionActive.value = false
      emit('resolutionChange', { size: null, image_size: null, aspect_ratio: null })
      return
    }
    resolutionActive.value = true
    emit('resolutionChange', {
      size: `${dims.width}x${dims.height}`,
      image_size: baseSize.value,   // 选档位时同时把 "1K"/"2K"/"4K" 抛出去
      aspect_ratio: aspectRatio.value,
    })
  } else {
    // 自定义：把用户输入的宽高对齐到 16 的倍数后再发出去
    resolutionActive.value = true
    const alignedW = alignToStep(customWidth.value || 0)
    const alignedH = alignToStep(customHeight.value || 0)
    const sizeStr = `${alignedW}x${alignedH}`
    emit('resolutionChange', {
      size: sizeStr,
      image_size: null,             // 自定义宽高没有档位概念
      aspect_ratio: null,
    })
  }
  closeResolutionMenu()
}

/**
 * 处理输入变化
 */
function handleInput(event: Event) {
  const target = event.target as HTMLTextAreaElement
  emit('update:modelValue', target.value)
  adjustHeight()
}

/**
 * 处理回车键
 */
function handleEnter(e: KeyboardEvent) {
  if (e.shiftKey) return // 允许 Shift+Enter 换行
  emit('generate')
}

/**
 * 自动调整输入框高度
 */
function adjustHeight() {
  const el = textareaRef.value
  if (!el) return

  el.style.height = 'auto'
  const newHeight = Math.max(64, Math.min(el.scrollHeight, 200))
  el.style.height = newHeight + 'px'
}

/**
 * 处理图片上传
 */
function handleImageUpload(event: Event) {
  const target = event.target as HTMLInputElement
  if (!target.files) return

  const files = Array.from(target.files)
  files.forEach((file) => {
    // 限制最多 5 张图片
    if (uploadedImages.value.length >= 5) {
      return
    }
    // 创建预览 URL
    const preview = URL.createObjectURL(file)
    uploadedImages.value.push({ file, preview })
  })

  // 通知父组件
  emitImagesChange()

  // 清空 input，允许重复选择同一文件
  target.value = ''
}

/**
 * 移除图片
 */
function removeImage(index: number) {
  const img = uploadedImages.value[index]
  // 释放预览 URL
  URL.revokeObjectURL(img.preview)
  uploadedImages.value.splice(index, 1)

  // 通知父组件
  emitImagesChange()
}

/**
 * 通知父组件图片变化
 */
function emitImagesChange() {
  const files = uploadedImages.value.map(img => img.file)
  emit('imagesChange', files)
  ensureSequentialConsistency()
}

// ========== 参考图拖拽排序（基于 pointer 事件手写）==========
// 当前正在被按住并拖动的下标
const draggingIndex = ref<number | null>(null)
// 光标当前 hover 到的目标下标，用于高亮 drop 区
const dragOverIndex = ref<number | null>(null)
// 判定"真正开始拖动"的位移阈值，避免和点击误触
const DRAG_START_THRESHOLD = 5
let pointerStartX = 0
let pointerStartY = 0
let pointerActiveId: number | null = null
let pointerActiveTarget: HTMLElement | null = null
let pointerMoved = false

function onPointerDown(idx: number, event: PointerEvent) {
  if (uploadedImages.value.length <= 1 || props.loading) return
  if (event.button !== undefined && event.button !== 0) return

  // 阻止浏览器默认的图片选中/拖影，避免"整块拖起来"的错觉
  event.preventDefault()

  pointerStartX = event.clientX
  pointerStartY = event.clientY
  pointerActiveId = event.pointerId
  pointerActiveTarget = event.currentTarget as HTMLElement
  pointerMoved = false
  draggingIndex.value = idx

  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
  window.addEventListener('pointercancel', onPointerCancel)
}

function findIndexUnderPointer(clientX: number, clientY: number): number | null {
  const items = document.querySelectorAll<HTMLElement>(
    '.uploaded-images-track [data-drag-index]'
  )
  for (const el of items) {
    const rect = el.getBoundingClientRect()
    if (
      clientX >= rect.left &&
      clientX <= rect.right &&
      clientY >= rect.top &&
      clientY <= rect.bottom
    ) {
      const raw = el.getAttribute('data-drag-index')
      if (raw === null) return null
      const parsed = Number(raw)
      return Number.isNaN(parsed) ? null : parsed
    }
  }
  return null
}

function onPointerMove(event: PointerEvent) {
  if (draggingIndex.value === null) return
  if (pointerActiveId !== null && event.pointerId !== pointerActiveId) return

  const dx = event.clientX - pointerStartX
  const dy = event.clientY - pointerStartY
  if (!pointerMoved && Math.hypot(dx, dy) < DRAG_START_THRESHOLD) return

  if (!pointerMoved) {
    pointerMoved = true
    if (pointerActiveTarget) {
      try {
        pointerActiveTarget.setPointerCapture?.(event.pointerId)
      } catch {
        // ignore
      }
    }
  }

  dragOverIndex.value = findIndexUnderPointer(event.clientX, event.clientY)
}

function onPointerUp(event: PointerEvent) {
  if (pointerActiveId !== null && event.pointerId !== pointerActiveId) return

  const from = draggingIndex.value
  const to = pointerMoved ? findIndexUnderPointer(event.clientX, event.clientY) : null

  cleanupPointerDrag()

  if (from === null || to === null || from === to) return

  const list = uploadedImages.value.slice()
  const [moved] = list.splice(from, 1)
  list.splice(to, 0, moved)
  uploadedImages.value = list

  emitImagesChange()
}

function onPointerCancel() {
  cleanupPointerDrag()
}

function cleanupPointerDrag() {
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  window.removeEventListener('pointercancel', onPointerCancel)
  if (pointerActiveTarget && pointerActiveId !== null) {
    try {
      pointerActiveTarget.releasePointerCapture?.(pointerActiveId)
    } catch {
      // ignore
    }
  }
  pointerActiveTarget = null
  pointerActiveId = null
  pointerMoved = false
  draggingIndex.value = null
  dragOverIndex.value = null
}

/**
 * 清理所有预览 URL
 */
function clearPreviews() {
  uploadedImages.value.forEach(img => URL.revokeObjectURL(img.preview))
  uploadedImages.value = []
}

// 组件卸载时清理
onUnmounted(() => {
  clearPreviews()
})

// 暴露方法给父组件
defineExpose({
  clearPreviews
})
</script>

<style scoped>
/* 组合框容器 */
.composer-container {
  background: white;
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(0, 0, 0, 0.06);
}

/* 输入区域 */
.composer-input-wrapper {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.search-icon-static {
  flex-shrink: 0;
  padding-top: 8px;
  color: #999;
}

.composer-textarea {
  flex: 1;
  border: none;
  outline: none;
  font-size: 16px;
  line-height: 1.6;
  resize: none;
  min-height: 44px;
  max-height: 200px;
  padding: 8px 0;
  font-family: inherit;
  color: var(--text-main, #1a1a1a);
}

.composer-textarea::placeholder {
  color: #999;
}

.composer-textarea:disabled {
  background: transparent;
  color: #999;
}

/* 已上传图片预览 */
.uploaded-images-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 16px;
  padding: 16px;
  background: #fafafa;
  border-radius: 12px;
  align-items: center;
}

.uploaded-images-track {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  touch-action: none;
  user-select: none;
}

.uploaded-image-item {
  position: relative;
  width: 60px;
  height: 60px;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  user-select: none;
  -webkit-user-drag: none;
  cursor: grab;
  transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease;
  touch-action: none;
}

.uploaded-image-item:active {
  cursor: grabbing;
}

.uploaded-image-item.is-dragging {
  opacity: 0.4;
}

.uploaded-image-item.is-drop-target {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(255, 36, 66, 0.35);
  outline: 2px dashed var(--primary, #ff2442);
  outline-offset: 2px;
}

.uploaded-image-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  user-select: none;
  -webkit-user-drag: none;
  pointer-events: none;
}

/* 序号徽标 */
.order-badge {
  position: absolute;
  top: 2px;
  left: 2px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  font-size: 11px;
  font-weight: 600;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}


.remove-image-btn {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.6);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  opacity: 0;
  transition: opacity 0.2s;
}

.uploaded-image-item:hover .remove-image-btn {
  opacity: 1;
}

.remove-image-btn:hover {
  background: var(--primary, #ff2442);
}

.upload-hint {
  flex: 1;
  font-size: 12px;
  color: var(--text-sub, #666);
  text-align: right;
}

/* 工具栏 */
.composer-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.toolbar-left {
  display: flex;
  gap: 8px;
}

.tool-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: #f5f5f5;
  border: none;
  cursor: pointer;
  color: #666;
  transition: all 0.2s;
}

.tool-btn:hover {
  background: #eee;
  color: var(--primary, #ff2442);
}

.tool-btn.active {
  background: rgba(255, 36, 66, 0.1);
  color: var(--primary, #ff2442);
}

.badge-count {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 18px;
  height: 18px;
  background: var(--primary, #ff2442);
  color: white;
  border-radius: 9px;
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 4px;
}

/* 生成张数控制 */
.page-count-control {
  position: relative;
}

.page-count-btn {
  width: auto;
  padding: 0 12px;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-sub, #666);
}

.page-count-btn .page-count-label {
  font-size: 13px;
  line-height: 1;
  white-space: nowrap;
}

.page-count-btn.active {
  background: rgba(255, 36, 66, 0.1);
  color: var(--primary, #ff2442);
}

.page-count-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-count-menu {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  z-index: 30;
  width: 280px;
  padding: 14px 16px 12px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.14), 0 0 0 1px rgba(0, 0, 0, 0.04);
  animation: pageCountMenuIn 0.15s ease-out;
}

@keyframes pageCountMenuIn {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.menu-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 13px;
  color: var(--text-main, #1a1a1a);
  font-weight: 600;
  margin-bottom: 10px;
}

.menu-value {
  font-size: 12px;
  font-weight: 500;
  color: var(--primary, #ff2442);
}

.quick-options {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 6px;
  margin-bottom: 12px;
}

.quick-option {
  padding: 6px 0;
  border: 1px solid #e8e8e8;
  background: #fafafa;
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-main, #1a1a1a);
  cursor: pointer;
  transition: all 0.15s;
}

.quick-option:hover {
  border-color: var(--primary, #ff2442);
  color: var(--primary, #ff2442);
}

.quick-option.active {
  background: var(--primary, #ff2442);
  border-color: var(--primary, #ff2442);
  color: white;
}

.slider-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.page-slider {
  flex: 1;
  accent-color: var(--primary, #ff2442);
  cursor: pointer;
}

.page-number {
  width: 64px;
  padding: 6px 8px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  font-size: 13px;
  text-align: center;
  outline: none;
  transition: border-color 0.15s;
}

.page-number:focus {
  border-color: var(--primary, #ff2442);
}

.menu-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.menu-btn {
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s;
}

.menu-btn.ghost {
  background: transparent;
  color: var(--text-sub, #666);
  border-color: #e0e0e0;
}

.menu-btn.ghost:hover {
  color: var(--text-main, #1a1a1a);
  border-color: #c0c0c0;
}

.menu-btn.primary {
  background: var(--primary, #ff2442);
  color: white;
}

.menu-btn.primary:hover {
  opacity: 0.92;
}

/* ========== 分辨率设置 ========== */
.resolution-control {
  position: relative;
}

.resolution-btn {
  width: auto;
  padding: 0 12px;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-sub, #666);
}

.resolution-btn .resolution-label {
  font-size: 13px;
  line-height: 1;
  white-space: nowrap;
}

.resolution-btn.active {
  background: rgba(255, 36, 66, 0.1);
  color: var(--primary, #ff2442);
}

.resolution-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.resolution-menu {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  z-index: 30;
  width: 360px;
  padding: 16px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.14), 0 0 0 1px rgba(0, 0, 0, 0.04);
  animation: pageCountMenuIn 0.15s ease-out;
}

.resolution-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 14px;
}

.resolution-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main, #1a1a1a);
}

.resolution-current {
  font-size: 12px;
  color: var(--text-sub, #888);
}

.resolution-tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px;
  padding: 4px;
  background: #f5f5f5;
  border-radius: 10px;
  margin-bottom: 16px;
}

.resolution-tab {
  padding: 7px 0;
  background: transparent;
  border: none;
  border-radius: 7px;
  font-size: 13px;
  color: var(--text-sub, #666);
  cursor: pointer;
  transition: all 0.15s;
}

.resolution-tab:hover {
  color: var(--text-main, #1a1a1a);
}

.resolution-tab.active {
  background: white;
  color: var(--text-main, #1a1a1a);
  font-weight: 600;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.section-label {
  font-size: 12px;
  color: var(--text-sub, #888);
  margin-bottom: 8px;
}

.size-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 14px;
}

.size-option {
  padding: 10px 0;
  background: #fafafa;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-main, #1a1a1a);
  cursor: pointer;
  transition: all 0.15s;
}

.size-option:hover {
  border-color: var(--primary, #ff2442);
  color: var(--primary, #ff2442);
}

.size-option.active {
  background: rgba(255, 36, 66, 0.08);
  border-color: var(--primary, #ff2442);
  color: var(--primary, #ff2442);
}

.ratio-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 14px;
}

.ratio-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 0;
  background: #fafafa;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
}

.ratio-option:hover {
  border-color: var(--primary, #ff2442);
}

.ratio-option.active {
  background: rgba(255, 36, 66, 0.08);
  border-color: var(--primary, #ff2442);
}

.ratio-icon {
  display: block;
  border: 1.5px solid #999;
  border-radius: 2px;
  background: transparent;
}

.ratio-option.active .ratio-icon {
  border-color: var(--primary, #ff2442);
}

.ratio-text {
  font-size: 12px;
  color: var(--text-main, #1a1a1a);
  line-height: 1;
}

.ratio-option.active .ratio-text {
  color: var(--primary, #ff2442);
  font-weight: 600;
}

.custom-size-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.custom-input {
  flex: 1;
  padding: 8px 10px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  font-size: 14px;
  text-align: center;
  outline: none;
  transition: border-color 0.15s;
}

.custom-input:focus {
  border-color: var(--primary, #ff2442);
}

.custom-x {
  color: var(--text-sub, #888);
  font-size: 14px;
}

.custom-hint {
  font-size: 12px;
  color: var(--text-sub, #999);
  margin-bottom: 14px;
}

.auto-hint {
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-sub, #666);
  line-height: 1.6;
  margin-bottom: 14px;
  text-align: center;
}

.resolution-preview {
  padding: 12px 14px;
  background: #f8f8f8;
  border-radius: 8px;
  margin-bottom: 14px;
}

.preview-label {
  font-size: 12px;
  color: var(--text-sub, #888);
  margin-bottom: 4px;
}

.preview-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-main, #1a1a1a);
}

/* 生成按钮 */
.generate-btn {
  padding: 10px 24px;
  font-size: 15px;
  border-radius: 100px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.generate-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 加载动画 */
.spinner-sm {
  width: 16px;
  height: 16px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* ========== 依次参考开关 ========== */
.sequential-ref-control {
  display: inline-flex;
  align-items: center;
  margin-left: 4px;
}

.sequential-switch {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 10px;
  height: 40px;
  border-radius: 10px;
  background: #f5f5f5;
  cursor: pointer;
  user-select: none;
  transition: all 0.2s;
}

.sequential-switch:hover:not(.disabled) {
  background: #eee;
}

.sequential-switch input[type="checkbox"] {
  position: absolute;
  opacity: 0;
  pointer-events: none;
  width: 0;
  height: 0;
}

.switch-track {
  position: relative;
  width: 30px;
  height: 16px;
  border-radius: 999px;
  background: #cfcfcf;
  transition: background 0.15s ease;
  flex-shrink: 0;
}

.switch-thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: white;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
  transition: transform 0.15s ease;
}

.sequential-switch input:checked + .switch-track {
  background: var(--primary, #ff2442);
}

.sequential-switch input:checked + .switch-track .switch-thumb {
  transform: translateX(14px);
}

.switch-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-sub, #666);
  white-space: nowrap;
  line-height: 1;
}

.sequential-switch input:checked ~ .switch-label {
  color: var(--primary, #ff2442);
}

.sequential-switch.disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.sequential-switch.disabled .switch-track {
  background: #d9d9d9;
}
</style>
