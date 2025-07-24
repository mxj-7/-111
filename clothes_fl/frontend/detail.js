console.log('detail.js开始加载');

const API_BASE = "http://localhost:8000";
const urlParams = new URLSearchParams(window.location.search);
const id = urlParams.get('id');
const detailDiv = document.getElementById('detail');

console.log('图片ID:', id);

// 标签选项
const tagOptions = {
    style: ["衬衫", "T恤", "连衣裙", "裤子", "裙子", "外套", "毛衣"],
    color: ["红色", "蓝色", "白色", "黑色", "灰色", "绿色", "黄色", "紫色", "粉色", "棕色"],
    tone: ["浅色调", "深色调", "中性色调", "亮色调"],
    collar: ["圆领", "V领", "高领", "翻领", "立领", "一字领", "方领", "心形领"],
    sleeve: ["长袖", "短袖", "无袖", "七分袖", "五分袖", "泡泡袖", "喇叭袖", "紧身袖"],
    shape: ["修身", "宽松", "直筒", "A字型", "H型", "X型"],
    length: ["超短", "短款", "中长款", "长款", "及膝", "及踝"],
    fabric: ["棉质", "丝质", "麻质", "毛料", "化纤", "混纺", "牛仔", "皮革"],
    pattern: ["纯色", "条纹", "格子", "印花", "刺绣", "蕾丝", "网纱"],
    craft: ["拼接", "褶皱", "抽绳", "拉链", "纽扣", "系带"],
    occasion: ["休闲", "正式", "运动", "居家", "派对", "职场", "度假"],
    season: ["春季", "夏季", "秋季", "冬季", "四季通用"],
    style_type: ["简约", "复古", "甜美", "帅气", "优雅", "个性", "时尚"]
};

function renderTagSelect(name, value, isEditing = false) {
    const options = tagOptions[name].map(opt => `<option value="${opt}"${opt === value ? ' selected' : ''}>${opt}</option>`).join("");
    if (isEditing) {
        return `<label>${name}：</label><select name="${name}" id="${name}-select"><option value="">未选择</option>${options}</select><br>`;
    } else {
        return `<div><strong>${name}：</strong>${value || '未识别'}</div>`;
    }
}

let isEditing = false;

// 强制应用三列布局的函数
function applyThreeColumnLayout() {
    // 强制设置标签网格为三列
    const tagsGrids = document.querySelectorAll('.tags-grid');
    tagsGrids.forEach(grid => {
        grid.style.display = 'grid';
        grid.style.gridTemplateColumns = 'repeat(3, 1fr)';
        grid.style.gap = '15px';
        grid.style.marginBottom = '20px';
        grid.style.width = '100%';
    });
    
    // 强制设置编辑表单网格为三列
    const editGrids = document.querySelectorAll('.edit-form-grid');
    editGrids.forEach(grid => {
        grid.style.display = 'grid';
        grid.style.gridTemplateColumns = 'repeat(3, 1fr)';
        grid.style.gap = '20px';
        grid.style.marginBottom = '25px';
    });
    
    console.log('已强制应用三列布局');
}

async function loadDetail() {
    try {
        const res = await fetch(`${API_BASE}/image/${id}`);
        if (!res.ok) {
            detailDiv.innerHTML = '<p>图片不存在</p>';
            return;
        }
        const data = await res.json();
        
        // 使用数据库中的AI识别标签，如果没有则使用默认值
        const aiTags = {};
        for (const key in tagOptions) {
            aiTags[key] = data[key] || '未识别';
        }
        
        renderPage(data, aiTags);
    } catch (error) {
        console.error('加载详情失败:', error);
        detailDiv.innerHTML = '<p>加载失败，请刷新重试</p>';
    }
}

function renderPage(data, aiTags) {
    let aiTagsHtml = '';
    let editFormHtml = '';
    
    // 生成标签网格HTML
    for (const key in tagOptions) {
        aiTagsHtml += `<div class="tag-item"><strong>${key}：</strong><span>${aiTags[key] || '未识别'}</span></div>`;
        editFormHtml += `
            <div class="form-group">
                <label for="${key}-select">${key}：</label>
                <select name="${key}" id="${key}-select">
                    <option value="">未选择</option>
                    ${tagOptions[key].map(opt => `<option value="${opt}"${opt === aiTags[key] ? ' selected' : ''}>${opt}</option>`).join("")}
                </select>
            </div>`;
    }
    
    detailDiv.innerHTML = `
        <div class="detail-image-container">
            <img src="${API_BASE}/imagefile/${data.filename}" alt="服装图片">
        </div>
        
        <div class="tags-container">
            <div id="ai-tags-section">
                <h3>🤖 AI识别标签</h3>
                <div class="tags-grid">
                    ${aiTagsHtml}
                </div>
                <div class="button-group">
                    <button id="edit-btn" class="btn-primary">✏️ 修改标签</button>
                </div>
            </div>
            
            <div id="edit-section" style="display:none;">
                <form id="edit-form">
                    <h3>✏️ 编辑标签</h3>
                    <div class="edit-form-grid">
                        ${editFormHtml}
                    </div>
                    <div class="button-group">
                        <button type="submit" class="btn-success">💾 保存标签</button>
                        <button type="button" id="cancel-btn" class="btn-secondary">❌ 取消</button>
                    </div>
                </form>
            </div>
        </div>
        
        <div class="button-group">
            <button id="delete-btn" class="btn-danger">🗑️ 删除图片</button>
            <button onclick="window.location.href='index.html'" class="btn-secondary">🔙 返回首页</button>
        </div>
    `;
    
    // 延迟绑定事件，确保DOM元素完全渲染
    setTimeout(() => {
        console.log('开始绑定事件');
        
        // 强制应用三列布局
        applyThreeColumnLayout();
        
        // 绑定编辑按钮事件
        const editBtn = document.getElementById('edit-btn');
        if (editBtn) {
            console.log('找到编辑按钮，绑定事件');
            editBtn.onclick = () => {
                document.getElementById('ai-tags-section').style.display = 'none';
                document.getElementById('edit-section').style.display = 'block';
                isEditing = true;
                // 切换到编辑模式后也要应用布局
                setTimeout(() => applyThreeColumnLayout(), 50);
            };
        }
        
        // 绑定取消按钮事件
        const cancelBtn = document.getElementById('cancel-btn');
        if (cancelBtn) {
            console.log('找到取消按钮，绑定事件');
            cancelBtn.onclick = () => {
                document.getElementById('ai-tags-section').style.display = 'block';
                document.getElementById('edit-section').style.display = 'none';
                isEditing = false;
                // 切换回显示模式后也要应用布局
                setTimeout(() => applyThreeColumnLayout(), 50);
            };
        }
        
        // 绑定保存表单事件
        const editForm = document.getElementById('edit-form');
        if (editForm) {
            console.log('找到编辑表单，绑定事件');
            editForm.onsubmit = async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                await fetch(`${API_BASE}/edit_tags/${id}`, {
                    method: 'POST',
                    body: formData
                });
                alert('标签已保存');
                loadDetail();
            };
        }
        
        // 绑定删除按钮事件
        const deleteBtn = document.getElementById('delete-btn');
        if (deleteBtn) {
            console.log('找到删除按钮，绑定事件');
            deleteBtn.onclick = function() {
                console.log('删除按钮被点击！');
                
                fetch(`${API_BASE}/delete/${id}`, {
                    method: 'POST'
                })
                .then(response => {
                    console.log('删除响应状态:', response.status);
                    return response.json();
                })
                .then(data => {
                    console.log('删除响应数据:', data);
                    alert('删除操作完成！响应: ' + JSON.stringify(data));
                    window.location.href = 'index.html';
                })
                .catch(error => {
                    console.error('删除出错:', error);
                    alert('删除出错: ' + error.message);
                });
            };
        } else {
            console.error('未找到删除按钮！');
        }
        
        console.log('事件绑定完成');
    }, 100);
}

// 确保DOM完全加载后再执行
window.addEventListener('load', function() {
    console.log('页面完全加载，开始加载详情页');
    loadDetail();
});

console.log('detail.js加载完成');