Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """" & WScript.ScriptFullName & "\..\foldermonitor.exe" & """", 0, False
