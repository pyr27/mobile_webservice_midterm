package com.example.mw_project

import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.lifecycleScope
import coil.compose.AsyncImage
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.asRequestBody
import org.json.JSONArray
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.*

// 서버 주소: 에뮬레이터에서는 10.0.2.2가 PC의 localhost를 가리킴
const val SITE_URL = "http://10.0.2.2:8000"

data class Post(
    val author: Int,
    val title: String,
    val text: String,
    val imageUrl: String?
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    PhotoBlogScreen()
                }
            }
        }
    }
}

@Composable
fun PhotoBlogScreen() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val client = remember { OkHttpClient() }

    var posts by remember { mutableStateOf<List<Post>>(emptyList()) }
    var statusText by remember { mutableStateOf("동기화 버튼을 눌러주세요") }
    var showUploadDialog by remember { mutableStateOf(false) }

    fun syncPosts() {
        scope.launch {
            statusText = "동기화 중..."
            try {
                val result = withContext(Dispatchers.IO) {
                    val request = Request.Builder().url("$SITE_URL/api_root/Post/").build()
                    client.newCall(request).execute().use { response ->
                        val body = response.body?.string() ?: "[]"
                        val arr = JSONArray(body)
                        (0 until arr.length()).map { i ->
                            val obj = arr.getJSONObject(i)
                            Post(
                                author = obj.optInt("author"),
                                title = obj.optString("title"),
                                text = obj.optString("text"),
                                imageUrl = obj.optString("image", null)
                            )
                        }
                    }
                }
                posts = result
                statusText = if (result.isEmpty()) "불러올 이미지가 없습니다." else "이미지 로드 성공!"
            } catch (e: Exception) {
                statusText = "동기화 실패: ${e.message}"
            }
        }
    }

    Column(modifier = Modifier.fillMaxSize().padding(12.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Button(onClick = { syncPosts() }, modifier = Modifier.weight(1f)) {
                Text("동기화")
            }
            Button(onClick = { showUploadDialog = true }, modifier = Modifier.weight(1f)) {
                Text("새로운 이미지 게시")
            }
        }

        Spacer(modifier = Modifier.height(8.dp))
        Text(statusText)
        Spacer(modifier = Modifier.height(8.dp))

        LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            items(posts) { post ->
                Column {
                    Text(post.title, style = MaterialTheme.typography.titleMedium)
                    if (!post.imageUrl.isNullOrEmpty()) {
                        AsyncImage(
                            model = post.imageUrl,
                            contentDescription = post.title,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(220.dp),
                            contentScale = ContentScale.Crop
                        )
                    }
                }
            }
        }
    }

    if (showUploadDialog) {
        UploadDialog(
            onDismiss = { showUploadDialog = false },
            onUpload = { title, text, imageUri ->
                scope.launch {
                    statusText = "업로드 중..."
                    try {
                        withContext(Dispatchers.IO) {
                            val now = SimpleDateFormat(
                                "yyyy-MM-dd'T'HH:mm:ssXXX", Locale.getDefault()
                            ).format(Date())

                            // content:// Uri -> 임시 파일로 복사 (멀티파트 전송을 위해)
                            val inputStream = context.contentResolver.openInputStream(imageUri)
                            val tempFile = File(context.cacheDir, "upload_temp.jpg")
                            FileOutputStream(tempFile).use { out ->
                                inputStream?.copyTo(out)
                            }

                            val requestBody = MultipartBody.Builder()
                                .setType(MultipartBody.FORM)
                                .addFormDataPart("author", "1")
                                .addFormDataPart("title", title)
                                .addFormDataPart("text", text)
                                .addFormDataPart("created_date", now)
                                .addFormDataPart("published_date", now)
                                .addFormDataPart(
                                    "image", tempFile.name,
                                    tempFile.asRequestBody("image/jpeg".toMediaTypeOrNull())
                                )
                                .build()

                            val request = Request.Builder()
                                .url("$SITE_URL/api_root/Post/")
                                .post(requestBody)
                                .build()

                            client.newCall(request).execute().use { response ->
                                if (!response.isSuccessful) {
                                    throw Exception("서버 응답 ${response.code}: ${response.body?.string()}")
                                }
                            }
                        }
                        statusText = "업로드 성공!"
                        showUploadDialog = false
                        syncPosts()
                    } catch (e: Exception) {
                        statusText = "업로드 실패: ${e.message}"
                    }
                }
            }
        )
    }
}

@Composable
fun UploadDialog(
    onDismiss: () -> Unit,
    onUpload: (title: String, text: String, imageUri: Uri) -> Unit
) {
    var title by remember { mutableStateOf("") }
    var text by remember { mutableStateOf("") }
    var selectedImageUri by remember { mutableStateOf<Uri?>(null) }

    val pickImageLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri: Uri? -> selectedImageUri = uri }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("새로운 이미지 게시") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = title,
                    onValueChange = { title = it },
                    label = { Text("Title") },
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = text,
                    onValueChange = { text = it },
                    label = { Text("Text") },
                    modifier = Modifier.fillMaxWidth()
                )
                Button(onClick = { pickImageLauncher.launch("image/*") }) {
                    Text(if (selectedImageUri == null) "이미지 선택" else "이미지 선택됨")
                }
                selectedImageUri?.let {
                    AsyncImage(
                        model = it,
                        contentDescription = null,
                        modifier = Modifier.fillMaxWidth().height(150.dp),
                        contentScale = ContentScale.Crop
                    )
                }
            }
        },
        confirmButton = {
            TextButton(
                onClick = {
                    val uri = selectedImageUri
                    if (title.isNotBlank() && uri != null) {
                        onUpload(title, text, uri)
                    }
                },
                enabled = title.isNotBlank() && selectedImageUri != null
            ) { Text("POST") }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("취소") }
        }
    )
}