import React from 'react';
import { Badge, Button, Card, CardTitle, CardBody, CardText, Form, FormGroup, Input, Label} from 'reactstrap'
import PropTypes from 'prop-types'


export default function About() {

    return (
        <div className="container">
        <Card>
          <CardBody>
            <CardTitle tag="h3">About </CardTitle>
            <CardText tag="div">
                <hr/>
                <h4>What is Gopublish?</h4>
            
                <p>
                    Gopublish aims to provide a public link service for GenOuest users.
                    Users will be able to <i>publish</i> data and generate public links to share (or add in data warehouses).
                </p>

                <h4>Warnings</h4>
                <p>Gopublish and GenOuest do not provide any backup of the data. Data persistence is the sole responsability of the user.</p>
                <p>Gopublish is a service dedicated to <i>long-term</i> publishing. Please refer to <a target="_newtab" rel="noopener noreferrer" href="https://data-access.cesgo.org">Data-access</a> for a short-term solution.</p>

                <h4>Related links</h4>
                <p>
                  <a target="_newtab" rel="noopener noreferrer" href="https://www.genouest.org/">The GenOuest platform</a>
                </p>
                <p>
                  <a target="_newtab" rel="noopener noreferrer" href="https://github.com/mboudet/gopublish">Github repository</a>
                </p>
                <h4>Need help?</h4>
                <p>
                  Use <a target="_newtab" rel="noopener noreferrer" href="https://github.com/mboudet/gopublish/issues">Github issues</a> to report a bug, get help or request for a new feature.
                </p>
            </CardText>
          </CardBody>
        </Card>
        </div>
    );
}
