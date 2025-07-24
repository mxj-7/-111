const API_BASE = "http://localhost:8000";

// --- 图片上传 ---
const uploadBtn = document.getElementById('upload-btn');
const imageInput = document.getElementById('image-input');

uploadBtn.addEventListener('click', async () => {
    console.log("1. 上传按钮被点击");

    const files = imageInput.files;
    console.log("2. 获取文件列表:", files);

    if (!files || files.length === 0) {
        alert("请先选择要上传的图片！");
        console.warn("没有选择文件。");
        return;
    }

    console.log(`3. 准备上传 ${files.length} 个文件`);

    for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            console.log(`4. 正在上传: ${file.name}`);
            const response = await fetch(`${API_BASE}/upload/`, {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                console.log(`5. 成功上传: ${file.name}`);
            } else {
                const errorData = await response.json();
                const errorMessage = `上传失败: ${errorData.detail || response.statusText}`;
                alert(errorMessage);
                console.error(errorMessage, errorData);
            }
        } catch (error) {
            alert(`上传出错: ${error.message}`);
            console.error('上传过程中发生网络错误:', error);
        }
    }

    console.log("6. 所有文件处理完毕，重置表单并刷新图库");
    document.getElementById('upload-form').reset();
    loadGallery();
});

// 加载图片库
async function loadGallery(query = "", tags = "") {
    console.log("🔍 开始加载图片库...");
    
    let url = `${API_BASE}/images/`;
    if (tags) {
        url = `${API_BASE}/search/?tags=${encodeURIComponent(tags)}`;
    }
    
    console.log("📡 请求URL:", url);
    
    try {
        const res = await fetch(url);
        console.log("📊 响应状态:", res.status, res.statusText);
        
        if (!res.ok) {
            console.error("❌ API请求失败:", res.status, res.statusText);
            return;
        }
        
        const data = await res.json();
        console.log("📦 返回的数据:", data);
        console.log("📊 图片数量:", data.length);
        
        const gallery = document.getElementById('gallery');
        gallery.innerHTML = '';
        
        if (data.length === 0) {
            gallery.innerHTML = '<p>暂无图片数据</p>';
            console.log("⚠️ 没有图片数据");
            return;
        }
        
        data.forEach((item, index) => {
            console.log(`🖼️ 渲染图片 ${index + 1}:`, item.filename, item.id);
            
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `
                <img src="${API_BASE}/imagefile/${item.filename}" alt="服装图片" 
                     style="cursor: pointer;" 
                     onclick="window.location.href='detail.html?id=${item.id}'" 
                     onerror="console.error('图片加载失败:', '${item.filename}')">
                <button onclick="window.location.href='detail.html?id=${item.id}'">详情</button>
                <p>ID: ${item.id} | ${item.filename}</p>
            `;
            gallery.appendChild(card);
        });
        
        console.log("✅ 图片库加载完成");
        
    } catch (error) {
        console.error("❌ 加载图片库时发生错误:", error);
        const gallery = document.getElementById('gallery');
        gallery.innerHTML = '<p>加载失败，请检查网络连接</p>';
    }
}

// 搜索功能
const searchBtn = document.getElementById('search-btn');
const resetBtn = document.getElementById('reset-btn');
searchBtn.onclick = () => {
    const tag = document.getElementById('search-input').value.trim();
    loadGallery("", tag);
};
resetBtn.onclick = () => {
    document.getElementById('search-input').value = '';
    loadGallery();
};

// 初始加载
loadGallery();