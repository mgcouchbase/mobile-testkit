// 
//  ReplicationMethods.cs
// 
//  Author:
//   Jim Borden  <jim.borden@couchbase.com>
// 
//  Copyright (c) 2017 Couchbase, Inc All rights reserved.
// 
//  Licensed under the Apache License, Version 2.0 (the "License");
//  you may not use this file except in compliance with the License.
//  You may obtain a copy of the License at
// 
//  http://www.apache.org/licenses/LICENSE-2.0
// 
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.
// 

using System;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.Net;

using Couchbase.Lite.Sync;
using Couchbase.Lite.Util;

using JetBrains.Annotations;

using Newtonsoft.Json.Linq;

using static Couchbase.Lite.Testing.DatabaseMethods;

namespace Couchbase.Lite.Testing
{
    internal static class ReplicationMethods
    {
        public static void ConfigureReplication([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            var targetUrl = new Uri(args.GetString("target_url"));
            var continous = args.Get("continuous") != null && args.GetBoolean("continuous");
            var replicatorType = ReplicatorType.PushAndPull;
            var replicatorArg = args.Get("replication_type");
            if (replicatorArg != null && !Enum.TryParse(replicatorArg, true, out replicatorType))
            {
                throw new ArgumentException($"Invalid value for replication_type: {replicatorArg}");
            }

            With<Database>(postBody, "source_db", db =>
            {
                var config = new ReplicatorConfiguration(db, targetUrl)
                {
                    ReplicatorType = replicatorType,
                    Continuous = continous
                };

                if (postBody.ContainsKey("auth"))
                {
                    var authDict = (postBody["auth"] as JObject)?.ToObject<IReadOnlyDictionary<string, object>>();
                    switch ((authDict?["type"] as string)?.ToLowerInvariant())
                    {
                        case "basic":
                            config.Authenticator = new BasicAuthenticator(authDict["username"] as string, authDict["password"] as string);
                            break;
                        case "session":
                            config.Authenticator = new SessionAuthenticator(authDict["session"] as string,
                                authDict.ContainsKey("expires") ? (DateTimeOffset?)authDict.GetCast<DateTimeOffset>("expires") : null,
                                "SyncGatewaySession");
                            break;
                    }
                }

                response.WriteBody(MemoryMap.New<Replicator>(config));
            });
        }

        public static void StartReplication([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Replicator>(postBody, "replication_obj", r =>
            {
                r.Start();
                response.WriteEmptyBody();
            });
        }

        public static void StopReplication([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Replicator>(postBody, "replication_obj", r =>
            {
                r.Stop();
                response.WriteEmptyBody();
            });
        }

        public static void SetAuthenticator([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            var replicationConfig = "abc";
        }

        public static void ReplicationGetStatus([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Replicator>(postBody, "replication_obj", r => response.WriteBody(new Dictionary<string, object>
            {
                ["activity"] = r.Status.Activity.ToString(),
                ["total"] = r.Status.Progress.Total,
                ["completed"] = r.Status.Progress.Completed
            }));
        }
    }
}