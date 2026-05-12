using System.Diagnostics;
using System.Net.Http;
using System.Net.Sockets;
using System.Text.Json;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace JoyCaptionShell;

internal static class Program
{
    [STAThread]
    private static void Main(string[] args)
    {
        ApplicationConfiguration.Initialize();
        var url = "http://127.0.0.1:8765/";
        string? selfTestFile = null;
        string? selfTestOutput = null;

        for (var i = 0; i < args.Length; i++)
        {
            if (args[i] == "--self-test-file" && i + 1 < args.Length)
            {
                selfTestFile = args[++i];
            }
            else if (args[i] == "--self-test-output" && i + 1 < args.Length)
            {
                selfTestOutput = args[++i];
            }
            else if (!args[i].StartsWith("--", StringComparison.Ordinal))
            {
                url = args[i];
            }
        }

        Application.Run(new ShellForm(url, selfTestFile, selfTestOutput));
    }
}

internal sealed class ShellForm : Form
{
    private const int ServerPort = 8765;
    private const string ServerUrl = "http://127.0.0.1:8765/";

    private readonly WebView2 webView = new() { Dock = DockStyle.Fill };
    private readonly string url;
    private readonly string? selfTestFile;
    private readonly string? selfTestOutput;
    private Process? serverProcess;
    private bool ownsServerProcess;

    public ShellForm(string url, string? selfTestFile, string? selfTestOutput)
    {
        this.url = url;
        this.selfTestFile = selfTestFile;
        this.selfTestOutput = selfTestOutput;
        Text = "JoyCaption Desktop";
        Width = 1280;
        Height = 860;
        MinimumSize = new Size(980, 680);
        Icon = LoadWindowIcon();
        Controls.Add(webView);
        Load += OnLoad;
        FormClosed += OnFormClosed;
    }

    private static Icon? LoadWindowIcon()
    {
        var candidates = new[]
        {
            Path.Combine(AppContext.BaseDirectory, "JoyCaption.ico"),
            Path.Combine(AppContext.BaseDirectory, "Assets", "JoyCaption.ico"),
            Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "Assets", "JoyCaption.ico")),
        };

        foreach (var candidate in candidates)
        {
            if (File.Exists(candidate))
            {
                return new Icon(candidate);
            }
        }

        return null;
    }

    private async void OnLoad(object? sender, EventArgs e)
    {
        try
        {
            await Task.Run(EnsureServerRunning);
            await webView.EnsureCoreWebView2Async();
            webView.CoreWebView2.Settings.AreDevToolsEnabled = true;
            webView.CoreWebView2.Settings.AreDefaultContextMenusEnabled = true;
            webView.CoreWebView2.WebMessageReceived += OnWebMessageReceived;
            webView.CoreWebView2.NavigationCompleted += OnNavigationCompleted;
            webView.CoreWebView2.Navigate(url);
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                this,
                $"JoyCaption 서버를 시작하지 못했습니다.\n\n{ex.Message}",
                "JoyCaption Desktop",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
            Close();
        }
    }

    private void EnsureServerRunning()
    {
        if (IsServerHealthy().GetAwaiter().GetResult())
        {
            return;
        }

        var root = FindAppRoot();
        var python = Path.Combine(root, ".sandbox-prototype", "runtime", "venv", "Scripts", "python.exe");
        if (!File.Exists(python))
        {
            throw new FileNotFoundException("앱 내 Python 런타임을 찾을 수 없습니다.", python);
        }

        var logDir = Path.Combine(root, ".sandbox-prototype", "logs");
        Directory.CreateDirectory(logDir);

        var startInfo = new ProcessStartInfo
        {
            FileName = python,
            WorkingDirectory = root,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
        };
        startInfo.ArgumentList.Add("-m");
        startInfo.ArgumentList.Add("joycaption_desktop.prototype_server");
        startInfo.ArgumentList.Add("--host");
        startInfo.ArgumentList.Add("127.0.0.1");
        startInfo.ArgumentList.Add("--port");
        startInfo.ArgumentList.Add(ServerPort.ToString());
        startInfo.ArgumentList.Add("--sandbox-root");
        startInfo.ArgumentList.Add(".sandbox-prototype");
        startInfo.ArgumentList.Add("--profile");
        startInfo.ArgumentList.Add("windows-nvidia-4bit");
        startInfo.ArgumentList.Add("--real-model");
        startInfo.Environment["PYTHONPATH"] = Path.Combine(root, "src");
        startInfo.Environment["PYTHONDONTWRITEBYTECODE"] = "1";
        startInfo.Environment["HF_HOME"] = Path.Combine(root, ".sandbox-prototype", "cache", "huggingface");
        startInfo.Environment["TRANSFORMERS_CACHE"] = Path.Combine(root, ".sandbox-prototype", "cache", "huggingface", "transformers");

        serverProcess = Process.Start(startInfo) ?? throw new InvalidOperationException("서버 프로세스를 시작하지 못했습니다.");
        ownsServerProcess = true;
        serverProcess.OutputDataReceived += (_, e) => AppendServerLog(logDir, e.Data);
        serverProcess.ErrorDataReceived += (_, e) => AppendServerLog(logDir, e.Data);
        serverProcess.BeginOutputReadLine();
        serverProcess.BeginErrorReadLine();

        var deadline = DateTime.UtcNow.AddSeconds(20);
        while (DateTime.UtcNow < deadline)
        {
            if (serverProcess.HasExited)
            {
                throw new InvalidOperationException($"서버가 바로 종료되었습니다. 종료 코드: {serverProcess.ExitCode}");
            }

            if (IsServerHealthy().GetAwaiter().GetResult())
            {
                return;
            }

            Thread.Sleep(300);
        }

        throw new TimeoutException("서버 시작 시간이 너무 오래 걸립니다.");
    }

    private static async Task<bool> IsServerHealthy()
    {
        try
        {
            using var client = new HttpClient { Timeout = TimeSpan.FromSeconds(1) };
            using var response = await client.GetAsync($"{ServerUrl}api/config");
            return response.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }

    private static string FindAppRoot()
    {
        var current = new DirectoryInfo(AppContext.BaseDirectory);
        while (current is not null)
        {
            var root = current.FullName;
            if (
                File.Exists(Path.Combine(root, "src", "joycaption_desktop", "prototype_server.py")) &&
                File.Exists(Path.Combine(root, ".sandbox-prototype", "runtime", "venv", "Scripts", "python.exe")))
            {
                return root;
            }

            current = current.Parent;
        }

        throw new DirectoryNotFoundException("JoyCaption 앱 루트 폴더를 찾을 수 없습니다.");
    }

    private static void AppendServerLog(string logDir, string? line)
    {
        if (string.IsNullOrWhiteSpace(line))
        {
            return;
        }

        try
        {
            File.AppendAllText(
                Path.Combine(logDir, "webview-server.log"),
                $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss}] {line}{Environment.NewLine}");
        }
        catch
        {
            // Logging must never block the desktop app.
        }
    }

    private void OnFormClosed(object? sender, FormClosedEventArgs e)
    {
        if (!ownsServerProcess || serverProcess is null)
        {
            return;
        }

        try
        {
            if (!serverProcess.HasExited)
            {
                serverProcess.Kill(entireProcessTree: true);
                serverProcess.WaitForExit(3000);
            }
        }
        catch
        {
            // The process may have already exited while the form was closing.
        }
        finally
        {
            serverProcess.Dispose();
            serverProcess = null;
            ownsServerProcess = false;
        }
    }

    private async void OnNavigationCompleted(object? sender, CoreWebView2NavigationCompletedEventArgs e)
    {
        if (selfTestFile is null)
        {
            return;
        }
        await webView.CoreWebView2.ExecuteScriptAsync("window.chrome.webview.postMessage({ type: 'pick-file' });");
    }

    private void OnWebMessageReceived(object? sender, CoreWebView2WebMessageReceivedEventArgs e)
    {
        try
        {
            using var doc = JsonDocument.Parse(e.WebMessageAsJson);
            var type = doc.RootElement.GetProperty("type").GetString();
            if (type == "pick-file")
            {
                PickFile();
            }
            else if (type == "pick-folder")
            {
                PickFolder();
            }
        }
        catch (Exception ex)
        {
            Post(new { type = "path-error", message = ex.Message });
        }
    }

    private void PickFile()
    {
        using var dialog = new OpenFileDialog
        {
            Title = "이미지 파일 열기",
            Filter = "이미지 파일 (*.jpg;*.jpeg;*.png;*.webp;*.bmp)|*.jpg;*.jpeg;*.png;*.webp;*.bmp",
            CheckFileExists = true,
            CheckPathExists = true,
            FilterIndex = 1,
            RestoreDirectory = true,
            Multiselect = false,
        };

        if (selfTestFile is not null)
        {
            StartDialogAutomation(selfTestFile);
        }

        if (dialog.ShowDialog(this) == DialogResult.OK)
        {
            var extension = Path.GetExtension(dialog.FileName).ToLowerInvariant();
            var allowed = new HashSet<string> { ".jpg", ".jpeg", ".png", ".webp", ".bmp" };
            if (!allowed.Contains(extension))
            {
                Post(new { type = "path-error", message = "이미지 파일만 선택할 수 있습니다." });
                return;
            }
            PostSelected("image", dialog.FileName);
        }
        else
        {
            PostSelected("image", "");
        }
    }

    private void PickFolder()
    {
        using var dialog = new FolderBrowserDialog
        {
            Description = "이미지 폴더 열기",
            ShowNewFolderButton = false,
            UseDescriptionForTitle = true,
        };

        if (dialog.ShowDialog(this) == DialogResult.OK)
        {
            PostSelected("folder", dialog.SelectedPath);
        }
        else
        {
            PostSelected("folder", "");
        }
    }

    private void PostSelected(string kind, string path)
    {
        Post(new { type = "path-selected", kind, path });
        if (selfTestOutput is not null)
        {
            File.WriteAllText(selfTestOutput, JsonSerializer.Serialize(new { kind, path }));
            BeginInvoke(() => Close());
        }
    }

    private static void StartDialogAutomation(string path)
    {
        var thread = new Thread(() =>
        {
            Thread.Sleep(1500);
            Clipboard.SetText(path);
            SendKeys.SendWait("^v");
            Thread.Sleep(250);
            SendKeys.SendWait("{ENTER}");
        });
        thread.SetApartmentState(ApartmentState.STA);
        thread.IsBackground = true;
        thread.Start();
    }

    private void Post(object payload)
    {
        webView.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(payload));
    }
}
