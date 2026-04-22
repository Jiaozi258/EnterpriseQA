<template>
  <el-container class="layout-container">
    <el-aside width="350px" class="sidebar">
      <div class="logo">
        <h2>🛡️ 企业知识库</h2>
      </div>
      
      <el-button type="primary" size="large" class="new-chat-btn" @click="startNewChat">
        <el-icon><Plus /></el-icon> 新建知识问答
      </el-button>

      <div class="section-title">历史问答记录</div>
      <div class="session-list">
        <div 
          v-for="s in sessionList" 
          :key="s.id" 
          :class="['session-item', { active: currentSessionId === s.id }]"
          @click="loadSession(s.id)"
        >
         <div style="display: flex; align-items: center; overflow: hidden;">
          <el-icon><ChatDotRound /></el-icon>
          <span class="session-title">{{ s.title }}</span>
        </div>
        <el-icon class="delete-icon" @click.stop="deleteSession(s.id)"><Close /></el-icon>
      </div> </div> 

      <el-divider border-style="dashed" />

      <div class="section-title">知识库档案管理</div>
      <div class="upload-area">
        <el-upload drag action="#" :http-request="handleUpload" :show-file-list="false" accept=".pdf">
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">拖拽 PDF 或 <em>点击上传</em></div>
        </el-upload>
      </div>
      
      <el-table :data="documentList" style="width: 100%; margin-top: 10px;" max-height="250" v-loading="isTableLoading" size="small" stripe>
        <el-table-column prop="name" label="文件名" show-overflow-tooltip />
        <el-table-column label="状态" width="70" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.status ? 'success' : 'info'" size="small">
              {{ scope.row.status ? '已入库' : '解析中' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="50" align="center">
          <template #default="scope">
            <el-button type="danger" :icon="Delete" circle size="small" @click="handleDelete(scope.row.id)" />
          </template>
        </el-table-column>
      </el-table>
    </el-aside>

    <el-container>
      <el-main class="chat-main">
        <div class="chat-window">
          <div class="messages">
            <div v-for="(msg, index) in chatHistory" :key="index" :class="['message-box', msg.role]">
              <div class="avatar">{{ msg.role === 'user' ? '🧑‍💻' : '🤖' }}</div>
              <div class="content">{{ msg.content }}</div>
            </div>
          </div>
        </div>
      </el-main>
      
      <el-footer class="chat-footer" height="auto">
        <el-input
          v-model="userInput"
          type="textarea"
          :rows="3"
          placeholder="问你所惑，答你所想"
          @keyup.enter.prevent="sendMessage"
        />
        <div class="footer-action">
          <el-button type="primary" :loading="isThinking" @click="sendMessage">
            发送 (Enter)
          </el-button>
        </div>
      </el-footer>
    </el-container>
  </el-container>
</template>

<script setup>
import { UploadFilled, Delete, Plus, ChatDotRound, Close } from '@element-plus/icons-vue'
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

const api = axios.create({ baseURL: 'http://127.0.0.1:8000' })

// --- 状态管理 ---
const userInput = ref('')
const isThinking = ref(false)

// 🚀 删除历史对话
const deleteSession = (sessionId) => {
  ElMessageBox.confirm('确定要删除这段对话记录吗？', '提示', {
    confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning'
  }).then(async () => {
    try {
      await api.delete(`/api/sessions/${sessionId}`)
      ElMessage.success('对话已删除')
      
      // 如果你删掉的正好是你当前正在看的对话，那就清空主屏幕
      if (currentSessionId.value === sessionId) {
        startNewChat() 
      }
      fetchSessions() // 重新拉取最新的左侧列表
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

// 🚀 会话管理
const sessionList = ref([])
const currentSessionId = ref(null)

const defaultGreeting = { role: 'assistant', content: '你好！我是企业内部知识助手。请问有什么我可以帮你的？' }
const chatHistory = ref([defaultGreeting])

const documentList = ref([])
const isTableLoading = ref(false)

// --- 初始化加载 ---
onMounted(() => {
  fetchDocuments()
  fetchSessions() // 网页打开时拉取历史记录
})

// --- 模块 1：会话与记忆逻辑 ---
// 获取历史会话列表
const fetchSessions = async () => {
  try {
    const res = await api.get('/api/sessions')
    sessionList.value = res.data
  } catch (error) {
    ElMessage.error('无法获取历史会话')
  }
}

// 切换到某个历史会话
const loadSession = async (sessionId) => {
  currentSessionId.value = sessionId
  chatHistory.value = [] // 先清空屏幕
  try {
    const res = await api.get(`/api/sessions/${sessionId}/messages`)
    chatHistory.value = res.data.length > 0 ? res.data : [defaultGreeting]
  } catch (error) {
    ElMessage.error('读取聊天记录失败')
  }
}

// 点击“新建对话”
const startNewChat = () => {
  currentSessionId.value = null
  chatHistory.value = [defaultGreeting]
}

// 核心问答逻辑 (携带记忆 ID)
const sendMessage = async () => {
  if (!userInput.value.trim()) return
  const question = userInput.value
  chatHistory.value.push({ role: 'user', content: question })
  userInput.value = ''
  isThinking.value = true
  
  try {
    // 如果当前在旧会话里，就把 ID 传给后端；如果是新对话，就不传
    const payload = { query: question }
    if (currentSessionId.value) {
      payload.session_id = currentSessionId.value
    }
    
    const res = await api.post('/api/chat', payload)
    chatHistory.value.push({ role: 'assistant', content: res.data.answer })
    
    // 如果是新建的对话，后端会返回新的 ID。我们需要更新状态并刷新左侧列表
    if (!currentSessionId.value && res.data.session_id) {
      currentSessionId.value = res.data.session_id
      fetchSessions() 
    }
  } catch (error) {
    chatHistory.value.push({ role: 'assistant', content: '❌ 后端连接失败或大模型罢工了...' })
  } finally {
    isThinking.value = false
  }
}

// --- 模块 2：文档管理逻辑 (保持不变) ---
const fetchDocuments = async () => {
  isTableLoading.value = true
  try {
    const res = await api.get('/api/documents')
    documentList.value = res.data
  } catch (error) {
    ElMessage.error('无法获取文档列表')
  } finally {
    isTableLoading.value = false
  }
}

const handleUpload = async (options) => {
  const file = options.file
  const formData = new FormData()
  formData.append('file', file)
  const loading = ElMessage({ message: `正在将 ${file.name} 注入知识库...`, type: 'info', duration: 0 })
  try {
    await api.post('/api/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
    loading.close()
    ElMessage.success('注入成功！')
    fetchDocuments() 
  } catch (error) {
    loading.close()
    ElMessage.error('上传失败：' + (error.response?.data?.detail || error.message))
  }
}

const handleDelete = async (docId) => {
  ElMessageBox.confirm('这将会把该文档的记忆从 AI 大脑中彻底抹除, 是否继续?', '危险操作', {
    confirmButtonText: '强制删除', cancelButtonText: '取消', type: 'warning',
  }).then(async () => {
    try {
      isTableLoading.value = true
      await api.delete(`/api/documents/${docId}`)
      ElMessage.success('该知识已被彻底清除')
      fetchDocuments()
    } catch (error) {
      ElMessage.error('删除失败')
    } finally {
      isTableLoading.value = false
    }
  }).catch(() => {})
}
</script>

<style>
/* 增加了一些企业级质感的 UI 样式 */
html, body, #app { height: 100%; margin: 0; background-color: #f5f7fa; font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif; }
.layout-container { height: 100vh; }
.sidebar { background-color: #fcfcfc; border-right: 1px solid #e4e7ed; padding: 20px; display: flex; flex-direction: column; }
.logo { text-align: center; color: #409EFF; margin-bottom: 20px; }
.new-chat-btn { width: 100%; margin-bottom: 20px; border-radius: 8px; }

/* 历史列表样式 */
.section-title { font-size: 13px; color: #909399; font-weight: bold; margin-bottom: 10px; margin-top: 10px; }
.session-list { flex: 1; overflow-y: auto; margin-bottom: 15px; }
.session-item { padding: 12px; border-radius: 6px; cursor: pointer; display: flex; align-items: center; justify-content: space-between; color: #606266; margin-bottom: 5px; transition: all 0.2s; }
.session-item:hover { background-color: #f0f2f5; }
.session-item.active { background-color: #ecf5ff; color: #409EFF; font-weight: bold; }
.session-title { margin-left: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; max-width: 200px;}
.delete-icon { color: #f56c6c; opacity: 0; transition: opacity 0.2s; padding: 4px; }
.session-item:hover .delete-icon { opacity: 1; }
.delete-icon:hover { background-color: #fef0f0; border-radius: 50%; }

/* 聊天区样式 */
.chat-main { padding: 0; display: flex; flex-direction: column; background: #fff;}
.chat-window { flex: 1; padding: 30px; overflow-y: auto; display: flex; flex-direction: column; }
.message-box { display: flex; margin-bottom: 25px; max-width: 75%; }
.message-box.user { align-self: flex-end; flex-direction: row-reverse; }
.message-box.assistant { align-self: flex-start; }
.avatar { font-size: 28px; margin: 0 15px; }
.content { background-color: #f4f6f8; padding: 15px 20px; border-radius: 12px; box-shadow: 0 2px 8px 0 rgba(0, 0, 0, 0.04); line-height: 1.6; color: #333; font-size: 15px;}
.user .content { background-color: #409EFF; color: white; border-radius: 12px 2px 12px 12px; }
.assistant .content { border-radius: 2px 12px 12px 12px; }
.chat-footer { background-color: #ffffff; border-top: 1px solid #e4e7ed; padding: 20px 40px; }
.footer-action { margin-top: 10px; text-align: right; }
</style>