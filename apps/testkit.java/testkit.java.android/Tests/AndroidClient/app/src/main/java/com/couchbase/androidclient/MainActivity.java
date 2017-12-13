package com.couchbase.androidclient;

import android.os.Bundle;
import android.support.v7.app.AppCompatActivity;

import com.couchbase.lite.Database;
import com.couchbase.lite.DatabaseChange;
import com.couchbase.lite.DatabaseChangeListener;
import com.couchbase.lite.DatabaseConfiguration;
import com.couchbase.lite.Document;
import com.couchbase.lite.Log;
import com.couchbase.lite.Replicator;
import com.couchbase.lite.ReplicatorConfiguration;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.Random;
import java.util.TimerTask;
import java.util.HashMap;
import java.util.Map;
import java.util.List;
import java.util.ArrayList;

public class MainActivity extends AppCompatActivity {

  private Database database;
  private Document doc;
  private Replicator replicator;
  private int numOfDocs;
  private long scenarioRunTimeMinutes;
  private String syncGatewayURL;

  @Override
  protected void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);

    numOfDocs = getIntent().getIntExtra("numOfDocs",0);
    scenarioRunTimeMinutes = getIntent().getLongExtra("scenarioRunTimeMinutes",0);
    syncGatewayURL = getIntent().getStringExtra("syncGatewayURL");
    // numOfDocs = 10;
    // scenarioRunTimeMinutes = 1;
    // syncGatewayURL = "blip://192.168.33.11:4985/db";

    if (syncGatewayURL == null || numOfDocs == 0 || scenarioRunTimeMinutes == 0) {
      Log.e("app", "Did not enter the values for one of them : syncGatewayURL, numOfDocs, scenarioRunTimeMinutes ");
      finish();
      return;
    }

    setContentView(R.layout.activity_main);
    DatabaseConfiguration config = new DatabaseConfiguration(this);

    Log.i("state", "Creating database");
    try {
      database = new Database("my-database", config);
    }
    catch(com.couchbase.lite.CouchbaseLiteException e){
        Log.e("Exception occurred while creating database ",e.getMessage());
    }

    database.addChangeListener(new DatabaseChangeListener() {
      @Override
      public void changed(DatabaseChange change) {
        Log.i("Database change listener", "%s", change);
      }
    });

    Log.i("state", "Replicating data");
    URI uri = null;
    try {
      uri = new URI(syncGatewayURL);
    } catch (URISyntaxException e) {
      e.printStackTrace();
    }
    ReplicatorConfiguration replConfig = new ReplicatorConfiguration(database, uri);
    replConfig.setContinuous(true);

    replicator = new Replicator(replConfig);
    replicator.start();

  }


  @Override
  protected void onStart() {
    int k = 0;
    long startTime, stopTime, minutesCounted = 0;
    super.onStart();

    try{
    //Create docs in batch
    database.inBatch(new TimerTask() {
      @Override
      public void run() {

        for (int i = 0; i < numOfDocs; i++) {
          doc = new Document("doc___" + i);
          Map<String, Object> docmap = new HashMap<String, Object>();
          docmap.put("type", "user");
          docmap.put("name", "user_" + i);
          doc.set(docmap);
          try {
            database.save(doc);
          }
          catch(com.couchbase.lite.CouchbaseLiteException ex){
            Log.e("Failed to save document ", ex.getMessage());
          }
        }
      }
    });
    }
    catch(com.couchbase.lite.CouchbaseLiteException ex){
      Log.e("Failed to create docs in batch ", ex.getMessage());
    }
    
    startTime = System.currentTimeMillis();

    //update random doc
    Random rand = new Random();
    Object doc_obj = new Object();
    while (minutesCounted < scenarioRunTimeMinutes) {
      int n = rand.nextInt(numOfDocs);
      doc = database.getDocument("doc___" + n);
      Map<String, Object> docmap = new HashMap<String, Object>();
      docmap.put("name", "user_" + k);
      doc.set(docmap);
      try {
        database.save(doc);
        Thread.sleep(1000);
      } catch (InterruptedException e) {
        Log.e("app", e.getMessage());
      }
      catch(com.couchbase.lite.CouchbaseLiteException ex){
        Log.e("Failed to save document ", ex.getMessage());
      }
      stopTime = System.currentTimeMillis();
      minutesCounted = ((stopTime - startTime) / 60000);
      k++;
    }

    for (int i = 0; i < numOfDocs; i++) {
      doc = database.getDocument("doc___" + i);
      System.out.println("document user value  for doc id is "+ doc.getObject("name")+" "+"doc___" + i);
    }
    //Deleting docs
    Log.i("TEST", "before count -> %d", database.getCount());
    Log.i("app", "Deleting docs");
    for (int i = 0; i < numOfDocs - 2; i++) {
      doc = database.getDocument("doc___" + i);
      try {
        database.delete(doc);
      }
      catch(com.couchbase.lite.CouchbaseLiteException ex){
          Log.e("Failed to delete document ", ex.getMessage());
      }
    }
    Log.i("TEST", "after count -> %d", database.getCount());
    replicator.stop();
    //database.delete();

  }
}
