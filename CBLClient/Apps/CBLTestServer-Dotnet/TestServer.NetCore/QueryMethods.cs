// 
//  QueryMethods.cs
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
using System.Reflection;

using Couchbase.Lite.Query;
using Couchbase.Lite.Util;

using JetBrains.Annotations;

using Microsoft.CodeAnalysis.CSharp.Scripting;
using Microsoft.CodeAnalysis.Scripting;

using static Couchbase.Lite.Testing.DatabaseMethods;

namespace Couchbase.Lite.Testing
{
    internal static class QueryMethods
    {
        [NotNull]
        private static readonly MethodInfo EncodeAsJSON = Type.GetType("Couchbase.Lite.Internal.Query.XQuery, Couchbase.Lite")
            .GetMethod("EncodeAsJSON", BindingFlags.NonPublic | BindingFlags.Instance);

        public static async void CompileQuery([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            var source = postBody.GetCast<string>("source");
            if (source == null)
            {
                throw new InvalidOperationException("Cannot compile query without source in POST body");
            }

            await AsyncWith<Database>(postBody, "database", async db =>
            {
                try
                {
                    var globals = new Globals { Db = db };
                    var options = ScriptOptions.Default
                        .WithReferences(typeof(Query.Query).GetTypeInfo().Assembly)
                        .AddImports("Couchbase.Lite")
                        .AddImports("Couchbase.Lite.Query");

                    var compiled = CSharpScript.Create<IQuery>($"return {source}", options, typeof(Globals));
                    compiled.Compile();
                    var state = await compiled.RunAsync(globals);
                    var json = EncodeAsJSON.Invoke(state.ReturnValue, null) as string;
                    response.WriteRawBody(json);
                }
                catch (Exception e)
                {
                    response.WriteBody(e.Message?.Replace("\r", "")?.Replace('\n', ' ') ?? String.Empty, false);
                }
            });
        }
    }

    public class Globals
    {
        #region Variables

        public Database Db;

        #endregion
    }
}