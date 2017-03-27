package main

import (
	"fmt"

	"github.com/couchbaselabs/sg-replicate"
	"github.com/couchbaselabs/sgload/sgload"
	"log"
	"time"
)

func main() {

	// ------------------------------------------------- Setup -----------------------------------------------------

	// Create an SGDataStore SG client
	sgUrl := "http://localhost:4984/db"
	sgAdminPort := 4985
	sgDataStore := sgload.NewSGDataStore(sgUrl, sgAdminPort, nil, false)

	testSessionID := sgload.NewUuid()

	// Create user credentials struct
	userCred := sgload.UserCred{
		Username: fmt.Sprintf("username_%s", testSessionID),
		Password: "password",
	}

	// Create a user
	channels := []string{"ABC"}
	sgDataStore.CreateUser(
		userCred,
		channels,
	)

	// Set SGDataStore to use that user from now on
	sgDataStore.SetUserCreds(userCred)

	// ------------------------------------------------- Repro -----------------------------------------------------

	// Create a doc
	doc := sgload.Document{}
	doc["foo"] = "bar"
	doc["channels"] = []string{"ABC"}
	docsToCreate := []sgload.Document{
		doc,
	}
	docs, err := sgDataStore.BulkCreateDocuments(docsToCreate, true)
	if err != nil {
		panic(fmt.Sprintf("Error creating docs: %v", err))
	}
	log.Printf("Created Docs: %+v", docs)

	latestRevChan := make(chan string)

	// In one goroutine, send updates to doc
	go func(docsMeta []sgload.DocumentMetadata) {
		for {
			var err error
			docsToUpdate := GetDocsToUpdateFromDocMeta(docsMeta, channels)
			docsMeta, err = sgDataStore.BulkCreateDocuments(docsToUpdate, true)
			if err != nil {
				panic(fmt.Sprintf("Error creating docs: %v", err))
			}
			log.Printf("Updated docs: %+v", docsMeta)
			docMeta := docsMeta[0]
			latestRevChan <- docMeta.Revision
			time.Sleep(time.Millisecond * 0)
		}

	}(docs)

	//// In another goroutine, read latest revision of that doc doc
	go func(docMeta []sgload.DocumentMetadata) {

		bulkGetRequest := CreateBulkGetRequestFromDocMeta(docMeta, docMeta[0].Revision)

		for {

			latestRev := <-latestRevChan

			log.Printf("Getting docs with bulk get request: %+v", bulkGetRequest)
			bulkGetReponse, err := sgDataStore.BulkGetDocuments(bulkGetRequest)
			if err != nil {
				panic(fmt.Sprintf("Error creating docs: %v", err))
			}
			log.Printf("Get docs: %+v", bulkGetReponse)
			bulkGetRequest = CreateBulkGetRequestFromBulkGetResponse(bulkGetReponse, latestRev)

			time.Sleep(time.Millisecond * 0)
		}

	}(docs)

	time.Sleep(time.Second * 30)

}

func CreateBulkGetRequestFromBulkGetResponse(docs []sgreplicate.Document, latestRevId string) sgreplicate.BulkGetRequest {

	docRevPairs := []sgreplicate.DocumentRevisionPair{}

	for _, sgrDoc := range docs {
		doc := sgload.DocumentFromSGReplicateDocument(sgrDoc)
		docRevPair := sgreplicate.DocumentRevisionPair{
			Id:       doc.Id(),
			Revision: latestRevId,
		}
		docRevPairs = append(docRevPairs, docRevPair)
	}

	bulkGetRequest := sgreplicate.BulkGetRequest{
		Docs: docRevPairs,
	}
	return bulkGetRequest

}

func CreateBulkGetRequestFromDocMeta(docsMeta []sgload.DocumentMetadata, latestRevId string) sgreplicate.BulkGetRequest {

	docRevPairs := []sgreplicate.DocumentRevisionPair{}

	for _, docMeta := range docsMeta {
		docRevPair := sgreplicate.DocumentRevisionPair{
			Id:       docMeta.Id,
			Revision: latestRevId,
		}
		docRevPairs = append(docRevPairs, docRevPair)
	}

	bulkGetRequest := sgreplicate.BulkGetRequest{
		Docs: docRevPairs,
	}
	return bulkGetRequest

}

func GetDocsToUpdateFromDocMeta(docsMeta []sgload.DocumentMetadata, channels []string) []sgload.Document {
	docsToUpdate := []sgload.Document{}
	for _, docMeta := range docsMeta {
		doc := sgload.Document{}
		doc.SetId(docMeta.Id)
		doc.SetRevision(docMeta.Revision)
		doc.SetChannels(channels)
		docsToUpdate = append(docsToUpdate, doc)
	}
	return docsToUpdate
}
