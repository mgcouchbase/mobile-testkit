// 
//  ReplicatorConfigurationMethods.cs
// 
//  Author:
//   Prasanna Gholap  <prasanna.gholap@couchbase.com>
// 
//  Copyright (c) 2018 Couchbase, Inc All rights reserved.
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
    public class ReplicatorConfigurationMethods
    {
        public static void Create([NotNull] NameValueCollection args,
                                                     [NotNull] IReadOnlyDictionary<string, object> postBody,
                                                     [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "sourceDb", sdb =>
            {
                if (postBody.ContainsKey("targetURI"))
                {
                    var targetUrl = new Uri(args.GetString("targetURI"));
                    var replicationConfig = MemoryMap.New<ReplicatorConfiguration>(sdb, targetUrl);
                    response.WriteBody(replicationConfig);
                }
                else if (postBody.ContainsKey("targetDb"))
                {
                    With<Database>(postBody, "targetDB", tdb => response.WriteBody(MemoryMap.New<ReplicatorConfiguration>(sdb, tdb)));
                }
                else{
                    throw new ArgumentException("Invalid value for replication_type");
                }
            });
        }

        //public static void Copy([NotNull] NameValueCollection args,
        //                                     [NotNull] IReadOnlyDictionary<string, object> postBody,
        //                                     [NotNull] HttpListenerResponse response)
        //{
        //    With<ReplicatorConfiguration>(postBody, "configuration", repConf => response.WriteBody(repConf.Copy());
        //}

        public static void GetAuthenticator([NotNull] NameValueCollection args,
                                            [NotNull] IReadOnlyDictionary<string, object> postBody,
                                            [NotNull] HttpListenerResponse response)
        {
            With<ReplicatorConfiguration>(postBody, "configuration", repConf => response.WriteBody(repConf.Authenticator));
        }

        public static void GetChannels([NotNull] NameValueCollection args,
                                    [NotNull] IReadOnlyDictionary<string, object> postBody,
                                    [NotNull] HttpListenerResponse response)
        {
            With<ReplicatorConfiguration>(postBody, "configuration", repConf => response.WriteBody(repConf.Channels));
        }

        public static void GetConflictResolver([NotNull] NameValueCollection args,
                                               [NotNull] IReadOnlyDictionary<string, object> postBody,
                                               [NotNull] HttpListenerResponse response)
        {
            With<ReplicatorConfiguration>(postBody, "configuration", repConf => response.WriteBody(repConf.ConflictResolver));
        }

        public static void GetDatabase([NotNull] NameValueCollection args,
                                       [NotNull] IReadOnlyDictionary<string, object> postBody,
                                       [NotNull] HttpListenerResponse response)
        {
            With<ReplicatorConfiguration>(postBody, "configuration", repConf => response.WriteBody(repConf.Database));
        }

        public static void GetDocumentIDs([NotNull] NameValueCollection args,
                                          [NotNull] IReadOnlyDictionary<string, object> postBody,
                                          [NotNull] HttpListenerResponse response)
        {
            With<ReplicatorConfiguration>(postBody, "configuration", repConf => response.WriteBody(repConf.DocumentIDs));
        }

        public static void GetPinnedServerCertificate([NotNull] NameValueCollection args,
                                                      [NotNull] IReadOnlyDictionary<string, object> postBody,
                                                      [NotNull] HttpListenerResponse response)
        {
            With<ReplicatorConfiguration>(postBody, "configuration", repConf => response.WriteBody(repConf.PinnedServerCertificate));
        }

        public static void GetReplicatorType([NotNull] NameValueCollection args,
                                             [NotNull] IReadOnlyDictionary<string, object> postBody,
                                             [NotNull] HttpListenerResponse response)
        {
            With<ReplicatorConfiguration>(postBody, "configuration", repConf => response.WriteBody(repConf.ReplicatorType.ToString()));
        }

        public static void GetTarget([NotNull] NameValueCollection args,
                                     [NotNull] IReadOnlyDictionary<string, object> postBody,
                                     [NotNull] HttpListenerResponse response)
        {
            With<ReplicatorConfiguration>(postBody, "configuration", repConf => response.WriteBody(repConf.Target.ToString()));
        }

        public static void IsContinuous([NotNull] NameValueCollection args,
                             [NotNull] IReadOnlyDictionary<string, object> postBody,
                             [NotNull] HttpListenerResponse response)
        {
            With<ReplicatorConfiguration>(postBody, "configuration", repConf => response.WriteBody(repConf.Continuous));
        }

        public static void SetAuthenticator([NotNull] NameValueCollection args,
                             [NotNull] IReadOnlyDictionary<string, object> postBody,
                             [NotNull] HttpListenerResponse response)
        {
            With<ReplicatorConfiguration>(postBody, "configuration", repConf => 
            {
                With<Authenticator>(postBody, "authenticator", auth => {
                    repConf.Authenticator = auth;
                    response.WriteEmptyBody();
                });
            });
        }

        public static void SetChannels([NotNull] NameValueCollection args,
                     [NotNull] IReadOnlyDictionary<string, object> postBody,
                     [NotNull] HttpListenerResponse response)
        {
            IList<string> channels = (IList<string>)postBody["channels"];
            With<ReplicatorConfiguration>(postBody, "configuration", repConf =>
            {
                repConf.Channels = channels;
            });
        }

        public static void SetConflictResolver([NotNull] NameValueCollection args,
             [NotNull] IReadOnlyDictionary<string, object> postBody,
             [NotNull] HttpListenerResponse response)
        {
            IList<string> channels = (IList<string>)postBody["channels"];
            With<ReplicatorConfiguration>(postBody, "configuration", repConf =>
            {
                With<IConflictResolver>(postBody, "conflictResolver", cr => {
                    repConf.ConflictResolver = cr;
                    response.WriteEmptyBody();
                });
            });
        }

        public static void SetContinuous([NotNull] NameValueCollection args,
             [NotNull] IReadOnlyDictionary<string, object> postBody,
             [NotNull] HttpListenerResponse response)
        {
            Boolean continuous = (Boolean)postBody["continuous"];
            With<ReplicatorConfiguration>(postBody, "configuration", repConf =>
            {
                repConf.Continuous = continuous;
            });
        }

        public static void SetDocumentIDs([NotNull] NameValueCollection args,
             [NotNull] IReadOnlyDictionary<string, object> postBody,
             [NotNull] HttpListenerResponse response)
        {
            IList<string> documentIds = (IList<string>)postBody["documentIds"];
            With<ReplicatorConfiguration>(postBody, "configuration", repConf =>
            {
                repConf.DocumentIDs = documentIds;
            });
        }

        //public static void setPinnedServerCertificate([NotNull] NameValueCollection args,
        //                                              [NotNull] IReadOnlyDictionary<string, object> postBody,
        //                                              [NotNull] HttpListenerResponse response)
        //{
        //    Byte cert = (Byte)postBody["cert"];
        //    IList<string> documentIds = (IList<string>)postBody["documentIds"];
        //    With<ReplicatorConfiguration>(postBody, "configuration", repConf =>
        //    {
        //        repConf.PinnedServerCertificate = cert;
        //    });
        //}
    }
}