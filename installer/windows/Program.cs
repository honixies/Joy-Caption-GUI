using System.Diagnostics;
using System.IO.Compression;
using System.Net.Http;
using System.Runtime.InteropServices;
using System.Text;

namespace JoyCaptionGuiSetup;

internal static class Program
{
    private const string RepoZipUrl = "https://github.com/honixies/Joy-Caption-GUI/archive/refs/heads/main.zip";

    [STAThread]
    private static int Main()
    {
        try
        {
            ApplicationConfiguration.Initialize();
            var installer = new Installer();
            installer.Run();
            MessageBox.Show(
                "JoyCaption GUI installation is complete.",
                "JoyCaption GUI Setup",
                MessageBoxButtons.OK,
                MessageBoxIcon.Information);
            return 0;
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                ex.Message,
                "JoyCaption GUI Setup",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
            return 1;
        }
    }

    private sealed class Installer
    {
        private readonly string installDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "JoyCaptionGUI");

        public void Run()
        {
            Directory.CreateDirectory(installDir);
            using var temp = new TempDir();
            var zipPath = Path.Combine(temp.Path, "source.zip");
            var localPayload = Path.Combine(AppContext.BaseDirectory, "JoyCaptionGUI-Payload.zip");
            if (File.Exists(localPayload))
            {
                File.Copy(localPayload, zipPath, overwrite: true);
            }
            else
            {
                DownloadSource(zipPath);
            }
            ZipFile.ExtractToDirectory(zipPath, temp.Path);
            var extractedRoot = Directory.GetDirectories(temp.Path, "Joy-Caption-GUI-*").FirstOrDefault()
                ?? Directory.GetDirectories(temp.Path, "JoyCaptionGUI-Payload").FirstOrDefault()
                ?? throw new DirectoryNotFoundException("Could not find extracted JoyCaption source folder.");

            CopyDirectory(extractedRoot, installDir);
            EnsureShellBuilt();
            PrepareRuntime();
            CreateShortcuts();
        }

        private static void DownloadSource(string zipPath)
        {
            using var client = new HttpClient();
            client.DefaultRequestHeaders.UserAgent.ParseAdd("JoyCaptionGUI-Setup/1.0");
            using var response = client.GetAsync(RepoZipUrl).GetAwaiter().GetResult();
            response.EnsureSuccessStatusCode();
            using var input = response.Content.ReadAsStream();
            using var output = File.Create(zipPath);
            input.CopyTo(output);
        }

        private void EnsureShellBuilt()
        {
            var exePath = Path.Combine(installDir, "dist", "win-x64-single", "JoyCaptionShell.exe");
            if (File.Exists(exePath))
            {
                return;
            }

            var project = Path.Combine(installDir, "app", "webview-shell", "JoyCaptionShell.csproj");
            if (!File.Exists(project))
            {
                throw new FileNotFoundException("JoyCaption shell project was not found.", project);
            }

            RunProcess(
                "dotnet",
                $"publish \"{project}\" -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -p:EnableCompressionInSingleFile=true -o \"{Path.GetDirectoryName(exePath)}\"",
                installDir);
        }

        private void PrepareRuntime()
        {
            var script = Path.Combine(installDir, "scripts", "setup_real_runtime.ps1");
            if (!File.Exists(script))
            {
                throw new FileNotFoundException("Runtime setup script was not found.", script);
            }

            RunProcess(
                "powershell.exe",
                $"-NoProfile -ExecutionPolicy Bypass -File \"{script}\"",
                installDir);
        }

        private void CreateShortcuts()
        {
            var exePath = Path.Combine(installDir, "dist", "win-x64-single", "JoyCaptionShell.exe");
            if (!File.Exists(exePath))
            {
                throw new FileNotFoundException("JoyCaption executable was not created.", exePath);
            }

            var desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
            var programs = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.StartMenu),
                "Programs",
                "JoyCaption GUI");
            Directory.CreateDirectory(programs);
            CreateShortcut(Path.Combine(desktop, "JoyCaption GUI.lnk"), exePath);
            CreateShortcut(Path.Combine(programs, "JoyCaption GUI.lnk"), exePath);
        }

        private static void CreateShortcut(string shortcutPath, string targetPath)
        {
            var shell = Activator.CreateInstance(Type.GetTypeFromProgID("WScript.Shell")!);
            try
            {
                dynamic shortcut = shell!.GetType().InvokeMember(
                    "CreateShortcut",
                    System.Reflection.BindingFlags.InvokeMethod,
                    null,
                    shell,
                    new object[] { shortcutPath })!;
                shortcut.TargetPath = targetPath;
                shortcut.WorkingDirectory = Path.GetDirectoryName(targetPath);
                shortcut.IconLocation = targetPath;
                shortcut.Save();
            }
            finally
            {
                if (shell is not null)
                {
                    Marshal.FinalReleaseComObject(shell);
                }
            }
        }

        private static void CopyDirectory(string sourceDir, string destinationDir)
        {
            Directory.CreateDirectory(destinationDir);
            foreach (var directory in Directory.EnumerateDirectories(sourceDir, "*", SearchOption.AllDirectories))
            {
                var target = Path.Combine(destinationDir, Path.GetRelativePath(sourceDir, directory));
                Directory.CreateDirectory(target);
            }

            foreach (var file in Directory.EnumerateFiles(sourceDir, "*", SearchOption.AllDirectories))
            {
                var relative = Path.GetRelativePath(sourceDir, file);
                if (ShouldSkip(relative))
                {
                    continue;
                }

                var target = Path.Combine(destinationDir, relative);
                Directory.CreateDirectory(Path.GetDirectoryName(target)!);
                File.Copy(file, target, overwrite: true);
            }
        }

        private static bool ShouldSkip(string relativePath)
        {
            var normalized = relativePath.Replace('\\', '/');
            return normalized.StartsWith(".git/", StringComparison.OrdinalIgnoreCase)
                || normalized.StartsWith(".sandbox-prototype/jobs/", StringComparison.OrdinalIgnoreCase)
                || normalized.StartsWith(".sandbox-prototype/logs/", StringComparison.OrdinalIgnoreCase)
                || normalized.StartsWith("app/webview-shell/bin/", StringComparison.OrdinalIgnoreCase)
                || normalized.StartsWith("app/webview-shell/obj/", StringComparison.OrdinalIgnoreCase);
        }

        private static void RunProcess(string fileName, string arguments, string workingDirectory)
        {
            var output = new StringBuilder();
            using var process = new Process
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = fileName,
                    Arguments = arguments,
                    WorkingDirectory = workingDirectory,
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true,
                },
            };
            process.OutputDataReceived += (_, e) => { if (e.Data is not null) output.AppendLine(e.Data); };
            process.ErrorDataReceived += (_, e) => { if (e.Data is not null) output.AppendLine(e.Data); };
            process.Start();
            process.BeginOutputReadLine();
            process.BeginErrorReadLine();
            process.WaitForExit();
            if (process.ExitCode != 0)
            {
                throw new InvalidOperationException($"{fileName} failed with exit code {process.ExitCode}.\n\n{output}");
            }
        }
    }

    private sealed class TempDir : IDisposable
    {
        public TempDir()
        {
            Path = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"JoyCaptionGUI-Setup-{Guid.NewGuid():N}");
            Directory.CreateDirectory(Path);
        }

        public string Path { get; }

        public void Dispose()
        {
            try
            {
                if (Directory.Exists(Path))
                {
                    Directory.Delete(Path, recursive: true);
                }
            }
            catch
            {
                // Temporary files can be left behind without breaking installation.
            }
        }
    }
}
