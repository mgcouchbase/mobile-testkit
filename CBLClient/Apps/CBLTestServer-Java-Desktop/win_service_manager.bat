echo off
set location=%1
set jar_name=%2
set service_name=%3
set status=%4


IF "%status%"=="start" (
   %service_name%.exe //IS//%service_name% --Install=%location%\bin\%service_name%.exe --Description=%service_name% --Jvm=auto --Classpath=%location%\lib\%jar_name% --StartMode=jvm --StartClass=com.couchbase.mobiletestkit.javatestserver.TestServerMain --StartMethod=windowsService --StartParams=start --StopMode=jvm --StopClass=com.couchbase.mobiletestkit.javatestserver.TestServerMain --StopMethod=windowsService --StopParams=stop --LogPath=%location%\logs --StdOutput=auto --StdError=auto
)
) ELSE (
  %service_name%.exe //DS//%service_name%
)



